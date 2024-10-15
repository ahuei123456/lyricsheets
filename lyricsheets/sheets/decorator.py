from abc import ABC, abstractmethod
from typing import Protocol


from backoff import on_exception, expo


class TokenBucket(ABC):
    @abstractmethod
    def consume(self, key: str, num_tokens: int):
        ...


class WithTokenBucket(Protocol):
    bucket: TokenBucket


def token_bucket(key: str, num_tokens: int):
    def _token_bucket(f):
        class RateLimitException(Exception):
            pass

        @on_exception(expo, exception=RateLimitException)
        def wrapper(self: WithTokenBucket, *args, **kwargs):
            if not self.bucket.consume(key=key, num_tokens=num_tokens):
                raise RateLimitException()

            return f(self, *args, **kwargs)

        return wrapper

    return _token_bucket
