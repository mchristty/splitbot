import time
import psutil
import asyncio
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    db_connections: int
    response_time: float
    active_users: int
    cache_hit_rate: float


class PerformanceMonitor:
    """Монитор производительности системы"""
    
    def __init__(self):
        self.metrics_history: list[PerformanceMetrics] = []
        self.max_history_size = 100
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 80.0,
            'db_connections': 40,
            'response_time': 5.0
        }
        self.is_monitoring = False
    
    def start_monitoring(self, interval: int = 60):
        """Запускает мониторинг с заданным интервалом"""
        self.is_monitoring = True
        asyncio.create_task(self._monitor_loop(interval))
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_monitoring = False
    
    async def _monitor_loop(self, interval: int):
        """Основной цикл мониторинга"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                self._store_metrics(metrics)
                self._check_alerts(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                await asyncio.sleep(interval)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Собирает текущие метрики системы"""
        # CPU и память
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Подсчет активных соединений с БД (примерная оценка)
        db_connections = len([conn for conn in psutil.net_connections() 
                             if conn.laddr.port == 5432])  # PostgreSQL порт
        
        # Время ответа (среднее за последние запросы)
        response_time = self._calculate_avg_response_time()
        
        # Активные пользователи (примерная оценка)
        active_users = self._estimate_active_users()
        
        # Cache hit rate
        cache_hit_rate = self._get_cache_hit_rate()
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            db_connections=db_connections,
            response_time=response_time,
            active_users=active_users,
            cache_hit_rate=cache_hit_rate
        )
    
    def _calculate_avg_response_time(self) -> float:
        """Вычисляет среднее время ответа"""
        # Здесь можно интегрировать с реальными метриками времени ответа
        # Пока возвращаем примерное значение
        return 0.5  # секунды
    
    def _estimate_active_users(self) -> int:
        """Оценивает количество активных пользователей"""
        # Здесь можно интегрировать с реальными метриками пользователей
        # Пока возвращаем примерное значение
        return 50
    
    def _get_cache_hit_rate(self) -> float:
        """Получает процент попаданий в кэш"""
        try:
            from cache_manager import cache_manager
            stats = cache_manager.get_stats()
            return stats.get('hit_rate', 0.0)
        except:
            return 0.0
    
    def _store_metrics(self, metrics: PerformanceMetrics):
        """Сохраняет метрики в историю"""
        self.metrics_history.append(metrics)
        
        # Ограничиваем размер истории
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """Проверяет метрики на превышение порогов"""
        alerts = []
        
        if metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1f}%")
        
        if metrics.db_connections > self.alert_thresholds['db_connections']:
            alerts.append(f"High DB connections: {metrics.db_connections}")
        
        if metrics.response_time > self.alert_thresholds['response_time']:
            alerts.append(f"Slow response time: {metrics.response_time:.2f}s")
        
        if alerts:
            for alert in alerts:
                pass
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Возвращает текущие метрики"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Возвращает сводку метрик"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = self.metrics_history[-10:]  # Последние 10 измерений
        
        return {
            "current": {
                "cpu_usage": recent_metrics[-1].cpu_usage,
                "memory_usage": recent_metrics[-1].memory_usage,
                "db_connections": recent_metrics[-1].db_connections,
                "response_time": recent_metrics[-1].response_time,
                "active_users": recent_metrics[-1].active_users,
                "cache_hit_rate": recent_metrics[-1].cache_hit_rate
            },
            "averages": {
                "cpu_usage": sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics),
                "memory_usage": sum(m.memory_usage for m in recent_metrics) / len(recent_metrics),
                "db_connections": sum(m.db_connections for m in recent_metrics) / len(recent_metrics),
                "response_time": sum(m.response_time for m in recent_metrics) / len(recent_metrics),
                "active_users": sum(m.active_users for m in recent_metrics) / len(recent_metrics),
                "cache_hit_rate": sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
            },
            "alerts": self._get_active_alerts()
        }
    
    def _get_active_alerts(self) -> list[str]:
        """Возвращает список активных предупреждений"""
        if not self.metrics_history:
            return []
        
        current = self.metrics_history[-1]
        alerts = []
        
        if current.cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append("High CPU usage")
        
        if current.memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append("High memory usage")
        
        if current.db_connections > self.alert_thresholds['db_connections']:
            alerts.append("High DB connections")
        
        if current.response_time > self.alert_thresholds['response_time']:
            alerts.append("Slow response time")
        
        return alerts


# Глобальный экземпляр монитора
performance_monitor = PerformanceMonitor()
