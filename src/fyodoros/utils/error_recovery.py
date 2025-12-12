# utils/error_recovery.py
"""
Error Recovery Utility.

Provides retry mechanisms, circuit breakers, and fallback strategies
to enhance system reliability.
"""

import time
import functools
import logging
from pathlib import Path

# Setup Error Logging
log_dir = Path.home() / ".fyodor" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "errors.log",
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s:%(message)s'
)

class CircuitBreakerOpenException(Exception):
    pass

class ErrorRecovery:
    """
    Utilities for error handling and recovery.
    """

    @staticmethod
    def retry(max_attempts=3, backoff_factor=2, exceptions=(Exception,)):
        """
        Decorator to retry a function with exponential backoff.

        Args:
            max_attempts (int): Maximum number of retries.
            backoff_factor (int): Multiplier for wait time.
            exceptions (tuple): Exceptions to catch and retry.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                attempts = 0
                delay = 1
                while attempts < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        attempts += 1
                        logging.error(f"Error in {func.__name__}: {e}. Retrying ({attempts}/{max_attempts})...")
                        if attempts == max_attempts:
                            logging.error(f"Max retries reached for {func.__name__}.")
                            raise
                        time.sleep(delay)
                        delay *= backoff_factor
            return wrapper
        return decorator

    @staticmethod
    def circuit_breaker(failure_threshold=3, recovery_timeout=60):
        """
        Decorator that implements the Circuit Breaker pattern.
        """
        def decorator(func):
            # State attached to the wrapper function
            func.failures = 0
            func.last_failure_time = 0
            func.state = "CLOSED" # CLOSED (working), OPEN (broken), HALF-OPEN (testing)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                now = time.time()

                if func.state == "OPEN":
                    if now - func.last_failure_time > recovery_timeout:
                        func.state = "HALF-OPEN"
                    else:
                        raise CircuitBreakerOpenException(f"Circuit is OPEN for {func.__name__}")

                try:
                    result = func(*args, **kwargs)
                    if func.state == "HALF-OPEN":
                        func.state = "CLOSED"
                        func.failures = 0
                    return result
                except Exception as e:
                    func.failures += 1
                    func.last_failure_time = now
                    logging.error(f"Circuit Breaker: Failure in {func.__name__} ({func.failures}/{failure_threshold})")

                    if func.failures >= failure_threshold:
                        func.state = "OPEN"
                        logging.error(f"Circuit Breaker: Opening circuit for {func.__name__}")
                    raise
            return wrapper
        return decorator

    @staticmethod
    def fallback(fallback_func):
        """
        Decorator to execute a fallback function on failure.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Primary function {func.__name__} failed: {e}. Executing fallback.")
                    return fallback_func(*args, **kwargs)
            return wrapper
        return decorator
