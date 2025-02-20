import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import aiofiles
import aiofiles.os
from utils.logger import logger

class CacheManager:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_hits = 0
        self.cache_misses = 0
        self.bytes_saved = 0
        os.makedirs(cache_dir, exist_ok=True)

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate a unique cache key based on screenshot parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str, format: str) -> str:
        """Get the full path for a cached screenshot"""
        return os.path.join(self.cache_dir, f"{cache_key}.{format}")

    async def get_cached_screenshot(self, params: Dict[str, Any], format: str) -> Optional[bytes]:
        """Try to get a cached screenshot if it exists and is valid"""
        cache_key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(cache_key, format)

        try:
            if not await aiofiles.os.path.exists(cache_path):
                self.cache_misses += 1
                return None

            # Check if cache is expired (older than 1 hour)
            stats = await aiofiles.os.stat(cache_path)
            cache_time = datetime.fromtimestamp(stats.st_mtime)
            if datetime.now() - cache_time > timedelta(hours=1):
                await aiofiles.os.remove(cache_path)
                self.cache_misses += 1
                return None

            async with aiofiles.open(cache_path, 'rb') as f:
                data = await f.read()
                self.cache_hits += 1
                self.bytes_saved += len(data)  # Учитываем сэкономленные байты
                return data

        except Exception as e:
            logger.error(f"Cache error: {str(e)}")
            self.cache_misses += 1
            return None

    async def cache_screenshot(self, params: Dict[str, Any], format: str, screenshot_data: bytes) -> None:
        """Save a screenshot to cache"""
        try:
            cache_key = self._generate_cache_key(params)
            cache_path = self._get_cache_path(cache_key, format)

            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(screenshot_data)

        except Exception as e:
            logger.error(f"Error caching screenshot: {str(e)}")

    async def clear_cache(self) -> Tuple[int, int]:
        """Clear all cached screenshots and return number of files and bytes cleared"""
        try:
            files_cleared = 0
            bytes_cleared = 0

            for filename in os.listdir(self.cache_dir):
                if filename.startswith('.'):  # Пропускаем скрытые файлы
                    continue

                file_path = os.path.join(self.cache_dir, filename)
                try:
                    stats = await aiofiles.os.stat(file_path)
                    bytes_cleared += stats.st_size
                    await aiofiles.os.remove(file_path)
                    files_cleared += 1
                except Exception as e:
                    logger.error(f"Error removing cache file {filename}: {str(e)}")

            # Сбрасываем статистику
            self.cache_hits = 0
            self.cache_misses = 0
            self.bytes_saved = 0

            return files_cleared, bytes_cleared

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0, 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": round(hit_rate, 2),
            "bytes_saved": self.bytes_saved,
            "mb_saved": round(self.bytes_saved / (1024 * 1024), 2)
        }