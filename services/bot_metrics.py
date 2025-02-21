import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger

@dataclass
class CommandMetric:
    command: str
    execution_time: float
    timestamp: datetime
    success: bool

@dataclass
class SystemMetric:
    cpu_percent: float
    memory_percent: float
    timestamp: datetime

class BotMetrics:
    def __init__(self):
        self.command_metrics: List[CommandMetric] = []
        self.system_metrics: List[SystemMetric] = []
        self.error_counts: Dict[str, int] = {}
        self.last_system_check = datetime.now()
        self.metrics_retention_hours = 24
        logger.info("BotMetrics initialized")

    def start_command_tracking(self, command: str) -> float:
        """Начинает отслеживание времени выполнения команды"""
        logger.debug(f"Starting tracking for command: {command}")
        return time.time()

    def end_command_tracking(self, command: str, start_time: float, success: bool = True):
        """Завершает отслеживание времени выполнения команды"""
        execution_time = time.time() - start_time
        self.command_metrics.append(
            CommandMetric(
                command=command,
                execution_time=execution_time,
                timestamp=datetime.now(),
                success=success
            )
        )
        logger.info(f"Command {command} executed in {execution_time:.2f}s (success={success})")
        self._cleanup_old_metrics()

    def track_error(self, error_type: str):
        """Отслеживает количество ошибок по типам"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        logger.warning(f"Error tracked: {error_type} (count: {self.error_counts[error_type]})")

    def update_system_metrics(self):
        """Обновляет метрики системы"""
        try:
            now = datetime.now()
            if now - self.last_system_check >= timedelta(minutes=1):
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()

                self.system_metrics.append(
                    SystemMetric(
                        cpu_percent=cpu_percent,
                        memory_percent=memory.percent,
                        timestamp=now
                    )
                )
                self.last_system_check = now
                logger.info(f"System metrics updated - CPU: {cpu_percent}%, Memory: {memory.percent}%")
                self._cleanup_old_metrics()

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    def get_performance_stats(self) -> Dict[str, any]:
        """Возвращает статистику производительности бота"""
        try:
            if not self.command_metrics:
                return {
                    "commands": {"average_time": 0, "success_rate": 100},
                    "system": {"cpu": 0, "memory": 0},
                    "errors": {"total": 0, "types": {}}
                }

            # Статистика команд
            recent_commands = [m for m in self.command_metrics 
                             if m.timestamp >= datetime.now() - timedelta(hours=1)]

            avg_time = sum(m.execution_time for m in recent_commands) / len(recent_commands) \
                      if recent_commands else 0
            success_rate = (sum(1 for m in recent_commands if m.success) / len(recent_commands) * 100) \
                          if recent_commands else 100

            # Системные метрики
            recent_system = [m for m in self.system_metrics 
                           if m.timestamp >= datetime.now() - timedelta(minutes=5)]
            avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system) \
                     if recent_system else 0
            avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system) \
                        if recent_system else 0

            return {
                "commands": {
                    "average_time": round(avg_time, 2),
                    "success_rate": round(success_rate, 1),
                    "total_executed": len(recent_commands)
                },
                "system": {
                    "cpu": round(avg_cpu, 1),
                    "memory": round(avg_memory, 1)
                },
                "errors": {
                    "total": sum(self.error_counts.values()),
                    "types": dict(self.error_counts)
                }
            }

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}

    def _cleanup_old_metrics(self):
        """Очищает старые метрики"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)

            self.command_metrics = [m for m in self.command_metrics if m.timestamp >= cutoff_time]
            self.system_metrics = [m for m in self.system_metrics if m.timestamp >= cutoff_time]

            # Очищаем счетчики ошибок раз в сутки
            if self.command_metrics and \
               (datetime.now() - self.command_metrics[0].timestamp).days >= 1:
                self.error_counts.clear()

        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")