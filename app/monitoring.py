"""
Monitoring and metrics collection for the Django Frame Processor application.
"""
import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


def monitor_performance(func_name=None):
    """Decorator to monitor function performance."""
    def decorator(func):
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"Performance: {name} executed in {execution_time:.3f}s")
                
                cache_key = f"perf_metrics_{name}"
                metrics = cache.get(cache_key, [])
                metrics.append({
                    'timestamp': time.time(),
                    'execution_time': execution_time,
                    'success': True
                })
                metrics = metrics[-100:]
                cache.set(cache_key, metrics, 3600)  # 1 hour
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Performance: {name} failed after {execution_time:.3f}s - {str(e)}")
                
                cache_key = f"perf_metrics_{name}"
                metrics = cache.get(cache_key, [])
                metrics.append({
                    'timestamp': time.time(),
                    'execution_time': execution_time,
                    'success': False,
                    'error': str(e)
                })
                metrics = metrics[-100:]
                cache.set(cache_key, metrics, 3600)
                
                raise
                
        return wrapper
    return decorator


class DatabaseMetrics:
    """Collect database performance metrics."""
    
    @staticmethod
    def get_query_count():
        """Get current query count for the request."""
        return len(connection.queries)
    
    @staticmethod
    def log_slow_queries(threshold=1.0):
        """Log queries that exceed the threshold time."""
        for query in connection.queries:
            time_taken = float(query['time'])
            if time_taken > threshold:
                logger.warning(f"Slow query ({time_taken}s): {query['sql'][:200]}...")


class CeleryMetrics:
    """Monitor Celery task performance."""
    
    @staticmethod
    def get_queue_length():
        """Get approximate queue length from Redis."""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active_tasks = inspect.active()
            if active_tasks:
                return sum(len(tasks) for tasks in active_tasks.values())
            return 0
        except Exception as e:
            logger.error(f"Error getting queue length: {e}")
            return -1
    
    @staticmethod
    def get_worker_status():
        """Get worker status information."""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            return stats if stats else {}
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {}


def collect_system_metrics():
    """Collect system-wide metrics for monitoring."""
    metrics = {
        'timestamp': time.time(),
        'database': {
            'query_count': DatabaseMetrics.get_query_count(),
        },
        'celery': {
            'queue_length': CeleryMetrics.get_queue_length(),
            'worker_status': CeleryMetrics.get_worker_status(),
        },
        'cache': {
            'redis_connected': True
        }
    }
    
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
    except Exception:
        metrics['cache']['redis_connected'] = False
    
    return metrics