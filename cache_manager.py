import asyncio
import time
from typing import Any, Optional, Dict


class CacheManager:
    """Менеджер кэширования для оптимизации производительности"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl  # Time to live в секундах
        self.access_times: Dict[str, float] = {}
        
    def _is_expired(self, key: str) -> bool:
        """Проверяет, истек ли срок действия кэша"""
        if key not in self.access_times:
            return True
        return time.time() - self.access_times[key] > self.ttl
    
    def _cleanup_expired(self):
        """Удаляет истекшие записи из кэша"""
        current_time = time.time()
        expired_keys = [
            key for key, access_time in self.access_times.items()
            if current_time - access_time > self.ttl
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _evict_lru(self):
        """Удаляет наименее недавно использованные записи"""
        if len(self.cache) >= self.max_size:
            # Находим ключ с самым старым временем доступа
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self.cache.pop(oldest_key, None)
            self.access_times.pop(oldest_key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кэша"""
        if key in self.cache and not self._is_expired(key):
            self.access_times[key] = time.time()
            return self.cache[key]['value']
        
        # Удаляем истекшую запись
        if key in self.cache:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Сохраняет значение в кэш"""
        self._cleanup_expired()
        self._evict_lru()
        
        self.cache[key] = {'value': value, 'created_at': time.time()}
        self.access_times[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Удаляет значение из кэша"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def clear(self) -> None:
        """Очищает весь кэш"""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
        }


# Глобальный экземпляр кэша
cache_manager = CacheManager()
