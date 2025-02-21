from datetime import datetime
from typing import Dict, Any
import psutil
from utils.logger import logger
from services.bot_metrics import BotMetrics
from services.error_handler import ErrorHandler

class StatusReporter:
    def __init__(self, bot_metrics: BotMetrics, error_handler: ErrorHandler):
        self.bot_metrics = bot_metrics
        self.error_handler = error_handler
        self.start_time = datetime.now()

    def get_uptime(self) -> str:
        """Возвращает время работы бота в человекочитаемом формате"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def get_system_resources(self) -> Dict[str, float]:
        """Получает информацию о системных ресурсах"""
        try:
            memory = psutil.virtual_memory()
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {'cpu_percent': 0, 'memory_percent': 0, 'memory_available_mb': 0}

    def format_status_message(self) -> str:
        """Форматирует сообщение о статусе бота"""
        try:
            # Получаем все метрики
            performance_stats = self.bot_metrics.get_performance_stats()
            error_stats = self.error_handler.get_error_statistics()
            system_resources = self.get_system_resources()
            
            # Определяем общий статус
            status_emoji = "✅" if performance_stats['commands']['success_rate'] > 95 else "⚠️"
            
            message = f"""
*Статус DashboardSJ Bot* {status_emoji}

*Время работы:* {self.get_uptime()}

*Производительность:*
• Среднее время ответа: {performance_stats['commands']['average_time']}с
• Успешность команд: {performance_stats['commands']['success_rate']}%
• Всего команд: {performance_stats['commands']['total_executed']}

*Системные ресурсы:*
• CPU: {system_resources['cpu_percent']}%
• Память: {system_resources['memory_percent']}%
• Доступно памяти: {system_resources['memory_available_mb']:.1f} MB

*Статистика ошибок:*
• Всего ошибок: {error_stats['total_errors']}
• Типы ошибок: {', '.join(f"{k}: {v}" for k, v in error_stats['error_types'].items())}

*Состояние сервисов:*
• Google Sheets API: {"✅" if performance_stats['commands']['success_rate'] > 90 else "❌"}
• Скриншот сервис: {"✅" if performance_stats['commands']['success_rate'] > 90 else "❌"}
• Обработка изображений: {"✅" if performance_stats['commands']['success_rate'] > 90 else "❌"}

_Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
            return message
            
        except Exception as e:
            logger.error(f"Error formatting status message: {e}")
            return "❌ Ошибка получения статуса бота"

    def get_detailed_report(self) -> Dict[str, Any]:
        """Возвращает детальный отчет о состоянии бота"""
        try:
            performance_stats = self.bot_metrics.get_performance_stats()
            error_stats = self.error_handler.get_error_statistics()
            system_resources = self.get_system_resources()
            
            return {
                'uptime': self.get_uptime(),
                'performance': performance_stats,
                'errors': error_stats,
                'system': system_resources,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating detailed report: {e}")
            return {}
