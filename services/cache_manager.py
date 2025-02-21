import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from utils.logger import logger
import shutil

class CacheManager:
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 500):
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.cache_hits = 0
        self.cache_misses = 0
        self.bytes_saved = 0
        self._metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self._metadata: Dict[str, Dict[str, Any]] = {}

        # Создаем директорию и загружаем метаданные
        os.makedirs(cache_dir, exist_ok=True)
        self._load_metadata()

    def _load_metadata(self):
        """Загрузка метаданных кэша из файла"""
        try:
            if os.path.exists(self._metadata_file):
                with open(self._metadata_file, 'r') as f:
                    self._metadata = json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache metadata: {e}")
            self._metadata = {}

    def _save_metadata(self):
        """Сохранение метаданных кэша"""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Генерация уникального ключа кэша на основе параметров"""
        # Добавляем временную метку с точностью до часа для версионирования
        params_with_time = dict(params)
        params_with_time['cache_hour'] = datetime.now().strftime('%Y%m%d%H')
        param_str = json.dumps(params_with_time, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str, format: str) -> str:
        """Получение полного пути для кэшированного скриншота"""
        return os.path.join(self.cache_dir, f"{cache_key}.{format}")

    def _check_and_clean_cache(self):
        """Проверка размера кэша и удаление старых файлов при необходимости"""
        try:
            total_size = 0
            cache_files = []

            # Собираем информацию о файлах кэша
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('.') or filename == "cache_metadata.json":
                    continue

                file_path = os.path.join(self.cache_dir, filename)
                stats = os.stat(file_path)
                cache_files.append({
                    'path': file_path,
                    'size': stats.st_size,
                    'mtime': stats.st_mtime
                })
                total_size += stats.st_size

            # Если размер кэша превышает лимит, удаляем старые файлы
            if total_size > self.max_size_mb * 1024 * 1024:
                # Сортируем файлы по времени последнего доступа
                cache_files.sort(key=lambda x: x['mtime'])

                # Удаляем старые файлы, пока размер не станет приемлемым
                for file_info in cache_files:
                    if total_size <= self.max_size_mb * 1024 * 1024:
                        break

                    try:
                        os.remove(file_info['path'])
                        total_size -= file_info['size']
                        # Удаляем метаданные
                        key = os.path.splitext(os.path.basename(file_info['path']))[0]
                        if key in self._metadata:
                            del self._metadata[key]
                    except Exception as e:
                        logger.error(f"Error removing cache file: {e}")

                self._save_metadata()

        except Exception as e:
            logger.error(f"Error in cache cleanup: {e}")

    def get_cached_screenshot(self, params: Dict[str, Any], format: str) -> Optional[bytes]:
        """Получение кэшированного скриншота с проверкой валидности"""
        cache_key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(cache_key, format)

        try:
            if not os.path.exists(cache_path):
                self.cache_misses += 1
                return None

            # Проверяем метаданные и валидность кэша
            metadata = self._metadata.get(cache_key, {})
            cache_time = metadata.get('created_at', 0)

            # Проверяем срок действия кэша (1 час)
            if datetime.now().timestamp() - cache_time > 3600:
                os.remove(cache_path)
                if cache_key in self._metadata:
                    del self._metadata[cache_key]
                self._save_metadata()
                self.cache_misses += 1
                return None

            # Чтение файла
            with open(cache_path, 'rb') as f:
                data = f.read()
                self.cache_hits += 1
                self.bytes_saved += len(data)

                # Обновляем статистику использования
                metadata['last_accessed'] = datetime.now().timestamp()
                metadata['access_count'] = metadata.get('access_count', 0) + 1
                self._save_metadata()

                return data

        except Exception as e:
            logger.error(f"Cache read error: {str(e)}")
            self.cache_misses += 1
            return None

    def cache_screenshot(self, params: Dict[str, Any], format: str, screenshot_data: bytes) -> None:
        """Сохранение скриншота в кэш с метаданными"""
        try:
            # Проверяем и очищаем кэш при необходимости
            self._check_and_clean_cache()

            cache_key = self._generate_cache_key(params)
            cache_path = self._get_cache_path(cache_key, format)

            # Сохраняем файл
            with open(cache_path, 'wb') as f:
                f.write(screenshot_data)

            # Обновляем метаданные
            self._metadata[cache_key] = {
                'created_at': datetime.now().timestamp(),
                'format': format,
                'size': len(screenshot_data),
                'params': params,
                'access_count': 0
            }

            self._save_metadata()
            logger.info(f"Screenshot cached successfully: {cache_key}")

        except Exception as e:
            logger.error(f"Error caching screenshot: {str(e)}")

    def clear_cache(self) -> Tuple[int, int]:
        """Очистка всего кэша с возвратом статистики"""
        try:
            files_cleared = 0
            bytes_cleared = 0

            for filename in os.listdir(self.cache_dir):
                if filename.startswith('.') or filename == "cache_metadata.json":
                    continue

                file_path = os.path.join(self.cache_dir, filename)
                try:
                    stats = os.stat(file_path)
                    bytes_cleared += stats.st_size
                    os.remove(file_path)
                    files_cleared += 1
                except Exception as e:
                    logger.error(f"Error removing cache file {filename}: {str(e)}")

            # Очищаем метаданные
            self._metadata = {}
            self._save_metadata()

            # Сбрасываем статистику
            self.cache_hits = 0
            self.cache_misses = 0
            self.bytes_saved = 0

            return files_cleared, bytes_cleared

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0, 0

    def get_stats(self) -> Dict[str, Any]:
        """Получение расширенной статистики использования кэша"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        # Подсчет общего размера кэша
        total_cache_size = sum(
            metadata.get('size', 0) 
            for metadata in self._metadata.values()
        )

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": round(hit_rate, 2),
            "bytes_saved": self.bytes_saved,
            "mb_saved": round(self.bytes_saved / (1024 * 1024), 2),
            "total_cache_size_mb": round(total_cache_size / (1024 * 1024), 2),
            "cache_entries": len(self._metadata),
            "cache_utilization": round((total_cache_size / (self.max_size_mb * 1024 * 1024)) * 100, 2)
        }