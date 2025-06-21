"""
Advanced retry utilities for Clonechat.

This module provides robust retry mechanisms with exponential backoff,
specific error handling, and configurable retry strategies.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Type, Union, List
from pyrogram.errors import FloodWait, ChatForwardsRestricted, NetworkError, BadRequest
from logging_config import get_logger, log_retry_attempt, log_flood_wait


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay in seconds for exponential backoff.
            max_delay: Maximum delay in seconds.
            exponential_base: Base for exponential backoff calculation.
            jitter: Whether to add random jitter to delays.
            retryable_exceptions: List of exception types that should trigger retry.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            FloodWait,
            NetworkError,
            BadRequest
        ]


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for a retry attempt using exponential backoff.
    
    Args:
        attempt: Current attempt number (0-based).
        config: Retry configuration.
        
    Returns:
        Delay in seconds.
    """
    if attempt == 0:
        return 0
    
    # Exponential backoff
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    
    # Add jitter if enabled
    if config.jitter:
        import random
        jitter_factor = 0.1  # 10% jitter
        jitter = delay * jitter_factor * random.random()
        delay += jitter
    
    # Cap at maximum delay
    return min(delay, config.max_delay)


def is_retryable_exception(exception: Exception, config: RetryConfig) -> bool:
    """
    Check if an exception should trigger a retry.
    
    Args:
        exception: The exception to check.
        config: Retry configuration.
        
    Returns:
        True if the exception should trigger a retry.
    """
    # Always retry on FloodWait
    if isinstance(exception, FloodWait):
        return True
    
    # Check against configured retryable exceptions
    for retryable_type in config.retryable_exceptions:
        if isinstance(exception, retryable_type):
            return True
    
    return False


def retry_on_exception(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    logger_name: Optional[str] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential backoff.
        jitter: Whether to add random jitter.
        retryable_exceptions: List of retryable exception types.
        logger_name: Logger name for retry logging.
        
    Returns:
        Decorated function.
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(logger_name or func.__module__)
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    if attempt == 0:
                        # First attempt
                        return await func(*args, **kwargs)
                    else:
                        # Retry attempt
                        delay = calculate_delay(attempt, config)
                        logger.warning(f"Retrying {func.__name__} in {delay:.1f} seconds (attempt {attempt}/{config.max_retries})")
                        await asyncio.sleep(delay)
                        return await func(*args, **kwargs)
                        
                except FloodWait as e:
                    wait_time = e.value
                    log_flood_wait(logger, wait_time)
                    await asyncio.sleep(wait_time)
                    last_exception = e
                    
                except Exception as e:
                    if not is_retryable_exception(e, config):
                        # Non-retryable exception, re-raise immediately
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt == config.max_retries:
                        # Final attempt failed
                        log_retry_attempt(logger, attempt + 1, config.max_retries, e)
                        logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                        raise last_exception or e
                    
                    # Log retry attempt
                    log_retry_attempt(logger, attempt + 1, config.max_retries, e)
                    last_exception = e
            
            # This should never be reached
            raise last_exception or Exception("Unexpected retry failure")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(logger_name or func.__module__)
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    if attempt == 0:
                        # First attempt
                        return func(*args, **kwargs)
                    else:
                        # Retry attempt
                        delay = calculate_delay(attempt, config)
                        logger.warning(f"Retrying {func.__name__} in {delay:.1f} seconds (attempt {attempt}/{config.max_retries})")
                        time.sleep(delay)
                        return func(*args, **kwargs)
                        
                except FloodWait as e:
                    wait_time = e.value
                    log_flood_wait(logger, wait_time)
                    time.sleep(wait_time)
                    last_exception = e
                    
                except Exception as e:
                    if not is_retryable_exception(e, config):
                        # Non-retryable exception, re-raise immediately
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt == config.max_retries:
                        # Final attempt failed
                        log_retry_attempt(logger, attempt + 1, config.max_retries, e)
                        logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                        raise last_exception or e
                    
                    # Log retry attempt
                    log_retry_attempt(logger, attempt + 1, config.max_retries, e)
                    last_exception = e
            
            # This should never be reached
            raise last_exception or Exception("Unexpected retry failure")
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_telegram_operation(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 120.0
):
    """
    Specialized decorator for Telegram API operations.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        
    Returns:
        Decorated function.
    """
    return retry_on_exception(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=[
            FloodWait,
            NetworkError,
            BadRequest
        ]
    )


def retry_file_operation(
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0
):
    """
    Specialized decorator for file operations.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        
    Returns:
        Decorated function.
    """
    return retry_on_exception(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=1.5,
        jitter=False,
        retryable_exceptions=[
            OSError,
            IOError,
            PermissionError
        ]
    )


class RetryableOperation:
    """Context manager for retryable operations."""
    
    def __init__(
        self,
        operation_name: str,
        config: Optional[RetryConfig] = None,
        logger_name: Optional[str] = None
    ):
        """
        Initialize retryable operation.
        
        Args:
            operation_name: Name of the operation for logging.
            config: Retry configuration.
            logger_name: Logger name.
        """
        self.operation_name = operation_name
        self.config = config or RetryConfig()
        self.logger = get_logger(logger_name or __name__)
        self.attempt = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is not None:
            if is_retryable_exception(exc_val, self.config):
                if self.attempt < self.config.max_retries:
                    self.attempt += 1
                    delay = calculate_delay(self.attempt, self.config)
                    log_retry_attempt(self.logger, self.attempt, self.config.max_retries, exc_val)
                    await asyncio.sleep(delay)
                    return False  # Don't suppress the exception
                else:
                    self.logger.error(f"All retry attempts failed for {self.operation_name}")
            else:
                self.logger.error(f"Non-retryable error in {self.operation_name}: {exc_val}")
        return False
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        if exc_type is not None:
            if is_retryable_exception(exc_val, self.config):
                if self.attempt < self.config.max_retries:
                    self.attempt += 1
                    delay = calculate_delay(self.attempt, self.config)
                    log_retry_attempt(self.logger, self.attempt, self.config.max_retries, exc_val)
                    time.sleep(delay)
                    return False  # Don't suppress the exception
                else:
                    self.logger.error(f"All retry attempts failed for {self.operation_name}")
            else:
                self.logger.error(f"Non-retryable error in {self.operation_name}: {exc_val}")
        return False


# Convenience functions for common retry patterns
async def retry_telegram_api_call(
    func: Callable,
    *args,
    max_retries: int = 3,
    **kwargs
) -> Any:
    """
    Retry a Telegram API call with appropriate error handling.
    
    Args:
        func: The function to call.
        *args: Arguments for the function.
        max_retries: Maximum number of retries.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        Result of the function call.
        
    Raises:
        Exception: If all retry attempts fail.
    """
    config = RetryConfig(max_retries=max_retries)
    logger = get_logger(__name__)
    
    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        except FloodWait as e:
            log_flood_wait(logger, e.value)
            await asyncio.sleep(e.value)
            
        except Exception as e:
            if not is_retryable_exception(e, config):
                raise
            
            if attempt == config.max_retries:
                logger.error(f"All retry attempts failed: {e}")
                raise
            
            log_retry_attempt(logger, attempt + 1, config.max_retries, e)
            delay = calculate_delay(attempt + 1, config)
            await asyncio.sleep(delay)
    
    raise Exception("Unexpected retry failure") 