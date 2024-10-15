from abc import abstractmethod
from collections.abc import Mapping

from lyricsheets.models import Song


class NotFoundError(Exception):
    pass


class SongService:
    @abstractmethod
    def get_song(self, songName: str) -> Song:
        ...

    @abstractmethod
    def get_format_tags(self, group: str = "") -> Mapping[str, str]:
        ...

    @abstractmethod
    def get_all_format_tags(self) -> Mapping[str, str]:
        ...

    @abstractmethod
    def create_song(self, song: Song, group: str = ""):
        ...

    @abstractmethod
    def update_song_karaoke(self, song: Song):
        ...
