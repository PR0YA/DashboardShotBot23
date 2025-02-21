import os
import psutil
import signal
from utils.logger import logger
from typing import List

class ProcessManager:
    @staticmethod
    def get_running_bot_processes() -> List[psutil.Process]:
        """Получает список процессов бота"""
        try:
            bot_processes = []
            logger.info(f"Searching for bot processes... Current PID: {os.getpid()}")

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'python' in proc.info['name'].lower() and 'main.py' in cmdline:
                        bot_processes.append(proc)
                        logger.info(f"Found bot process: PID={proc.pid}, CMD={cmdline}")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Could not access process: {e}")
                    continue

            logger.info(f"Found {len(bot_processes)} bot processes")
            return bot_processes
        except ImportError:
            logger.error("psutil not available")
            return []

    @staticmethod
    def cleanup_old_processes():
        """Очищает старые процессы бота"""
        current_pid = os.getpid()
        logger.info(f"Starting cleanup of old processes. Current PID: {current_pid}")

        # Получаем информацию о системных ресурсах
        virtual_memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"System resources - Memory: {virtual_memory.percent}%, CPU: {cpu_percent}%")

        try:
            # Сначала пытаемся удалить все PID файлы
            if os.path.exists("bot.pid"):
                try:
                    os.remove("bot.pid")
                    logger.info("Removed existing PID file")
                except Exception as e:
                    logger.error(f"Error removing PID file: {e}")

            # Ищем все процессы бота
            for proc in ProcessManager.get_running_bot_processes():
                if proc.pid != current_pid:
                    try:
                        logger.info(f"Attempting to terminate process {proc.pid}")

                        # Сначала пробуем мягкое завершение
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            logger.info(f"Process {proc.pid} terminated successfully")
                        except psutil.TimeoutExpired:
                            logger.warning(f"Timeout waiting for process {proc.pid} to terminate, using SIGKILL")
                            # Если не удалось завершить мягко, используем SIGKILL
                            os.kill(proc.pid, signal.SIGKILL)
                            try:
                                proc.wait(timeout=3)
                                logger.info(f"Process {proc.pid} killed successfully")
                            except psutil.TimeoutExpired:
                                logger.error(f"Failed to kill process {proc.pid}")

                    except psutil.NoSuchProcess:
                        logger.info(f"Process {proc.pid} already terminated")
                    except Exception as e:
                        logger.error(f"Error handling process {proc.pid}: {e}")

        except Exception as e:
            logger.error(f"Error in cleanup_old_processes: {e}")
            raise

    @staticmethod
    def is_bot_running() -> bool:
        """Проверяет, запущен ли уже бот"""
        try:
            current_pid = os.getpid()
            logger.info(f"Checking if bot is already running... Current PID: {current_pid}")

            running_processes = ProcessManager.get_running_bot_processes()
            other_processes = [p for p in running_processes if p.pid != current_pid]

            if other_processes:
                for proc in other_processes:
                    try:
                        cmdline = ' '.join(proc.cmdline())
                        logger.warning(f"Found another bot instance: PID={proc.pid}, CMD={cmdline}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.error(f"Error accessing process {proc.pid}: {e}")
                        continue
                return True

            logger.info("No other bot instances found")
            return False

        except Exception as e:
            logger.error(f"Error in is_bot_running: {e}")
            return False

    @staticmethod
    def save_pid():
        """Сохраняет PID текущего процесса"""
        try:
            pid = os.getpid()
            with open("bot.pid", 'w') as f:
                f.write(str(pid))
            logger.info(f"Saved PID file with PID: {pid}")
        except Exception as e:
            logger.error(f"Error saving PID file: {e}")

    @staticmethod
    def remove_pid():
        """Удаляет PID файл"""
        try:
            os.remove("bot.pid")
            logger.info("Successfully removed PID file")
        except Exception as e:
            logger.error(f"Error removing PID file: {e}")
