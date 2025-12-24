# utils/error_recovery.py
"""
Error Recovery & Retry Logic.

Provides decorators and utilities for robust error handling, retries with backoff,
and circuit breaking.
"""

import time
import functools
import logging
from typing import Type, Tuple, Optional, Callable
from pathlib import Path

# Configure logging
log_path = Path.home() / ".loop" / "logs" / "errors.log"
log_path.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(log_path),
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ErrorRecovery")


class ErrorRecovery:
    """
    Utilities for error recovery.
    """

    @staticmethod
    def retry_with_backoff(
        retries: int = 3,
        backoff_in_seconds: int = 1,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Decorator to retry a function with exponential backoff.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                x = 0
                while True:
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if x == retries:
                            logger.error(f"Failed after {retries} retries: {e}")
                            raise

                        sleep = (backoff_in_seconds * 2 ** x)
                        logger.warning(f"Error: {e}. Retrying in {sleep}s...")
                        time.sleep(sleep)
                        x += 1
            return wrapper
        return decorator

    @staticmethod
    def circuit_breaker(
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """
        Decorator to implement circuit breaker pattern.
        """
        def decorator(func):
            failures = 0
            last_failure_time = 0

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal failures, last_failure_time

                if failures >= failure_threshold:
                    if time.time() - last_failure_time < recovery_timeout:
                         raise RuntimeError("Circuit Breaker Open: Too many failures.")
                    else:
                        # Reset (Half-Open state effectively)
                        failures = 0

                try:
                    result = func(*args, **kwargs)
                    failures = 0 # Success resets
                    return result
                except Exception as e:
                    failures += 1
                    last_failure_time = time.time()
                    raise e
            return wrapper
        return decorator
