from typing import Optional, Dict, Any
from datetime import datetime
from utils.logger import logger
from services.process_manager import ProcessManager
from services.bot_metrics import BotMetrics

class ErrorHandler:
    def __init__(self, bot_metrics: BotMetrics):
        self.bot_metrics = bot_metrics
        self.error_details: Dict[str, Any] = {}

    def handle_error(self, error: Exception, context: Optional[Dict] = None) -> str:
        """
        Обрабатывает ошибки бота с расширенным логированием и отслеживанием

        Args:
            error: Объект исключения
            context: Контекст ошибки (опционально)

        Returns:
            str: Сообщение об ошибке для пользователя
        """
        try:
            error_type = type(error).__name__
            error_message = str(error)

            # Сохраняем детали ошибки
            error_details = {
                'timestamp': datetime.now().isoformat(),
                'type': error_type,
                'message': error_message,
                'context': context or {}
            }

            # Добавляем информацию о процессе
            current_pid = ProcessManager.get_running_bot_processes()
            process_info = f"Current PID: {current_pid}"

            try:
                # Получаем информацию о других процессах бота
                other_processes = [p for p in ProcessManager.get_running_bot_processes() 
                                 if p.pid != current_pid]
                if other_processes:
                    process_info += "\nOther bot processes found:"
                    for proc in other_processes:
                        try:
                            cmdline = ' '.join(proc.cmdline())
                            process_info += f"\n- PID={proc.pid}, CMD={cmdline}"
                        except Exception:
                            process_info += f"\n- PID={proc.pid} (inaccessible)"

                error_details['process_info'] = process_info
                logger.error(f"Process state when error occurred: {process_info}")

            except Exception as e:
                logger.error(f"Error getting process information: {e}")

            # Проверяем на конфликт процессов
            if "Conflict: terminated by other getUpdates request" in error_message:
                logger.error(f"Обнаружен конфликт: несколько экземпляров бота запущены одновременно\n{process_info}")
                # Пытаемся очистить процессы при обнаружении конфликта
                try:
                    ProcessManager.cleanup_old_processes()
                except Exception as e:
                    logger.error(f"Error cleaning up processes after conflict: {e}")
                return "Обнаружен конфликт процессов. Выполняется перезапуск бота..."

            # Отслеживаем ошибку в метриках
            self.bot_metrics.track_error(error_type)

            # Детальное логирование
            logger.error(
                f"Error details:\n"
                f"Type: {error_type}\n"
                f"Message: {error_message}\n"
                f"Context: {context}\n"
                f"Process info: {process_info}"
            )

            # Сохраняем для последующего анализа
            self.error_details[datetime.now().isoformat()] = error_details

            # Очищаем старые записи об ошибках (оставляем только последние 100)
            if len(self.error_details) > 100:
                oldest_key = min(self.error_details.keys())
                del self.error_details[oldest_key]

            return "Произошла ошибка при обработке запроса. Попробуйте позже."

        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return "Произошла внутренняя ошибка системы."

    def get_error_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по ошибкам"""
        try:
            total_errors = len(self.error_details)
            error_types = {}
            recent_errors = []

            for timestamp, details in sorted(
                self.error_details.items(), 
                key=lambda x: x[0], 
                reverse=True
            )[:10]:  # Последние 10 ошибок
                error_type = details['type']
                error_types[error_type] = error_types.get(error_type, 0) + 1
                recent_errors.append({
                    'timestamp': timestamp,
                    'type': error_type,
                    'message': details['message']
                })

            return {
                'total_errors': total_errors,
                'error_types': error_types,
                'recent_errors': recent_errors
            }

        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {}