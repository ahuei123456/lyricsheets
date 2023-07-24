from abc import ABC, abstractmethod
from typing import Optional, Protocol


class Cache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        ...

    @abstractmethod
    def set(self, key: str, val: bytes):
        ...


class Cacheable(Protocol):
    cache: Cache
