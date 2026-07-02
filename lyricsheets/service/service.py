from abc import abstractmethod
from collections.abc import Mapping, Sequence

from lyricsheets.models import Song


class NotFoundError(Exception):
    pass


class SongService:
    @abstractmethod
    def get_song(self, songName: str) -> Song: ...

    @abstractmethod
    def get_format_tags(self, group: str = "") -> Mapping[str, str]: ...

    @abstractmethod
    def get_all_format_tags(self) -> Mapping[str, str]: ...

    @abstractmethod
    def create_song(self, song: Song, group: str = ""): ...

    @abstractmethod
    def update_song_karaoke(self, song: Song): ...


class FallbackSongService(SongService):
    """Tries each service in order, earlier services taking precedence."""

    def __init__(self, services: Sequence[SongService]) -> None:
        self.services = list(services)

    def get_song(self, songName: str) -> Song:
        for service in self.services:
            try:
                return service.get_song(songName)
            except NotFoundError:
                continue

        raise NotFoundError(songName)

    def get_format_tags(self, group: str = "") -> Mapping[str, str]:
        ret: dict[str, str] = {}
        for service in reversed(self.services):
            ret.update(service.get_format_tags(group))

        return ret

    def get_all_format_tags(self) -> Mapping[str, str]:
        ret: dict[str, str] = {}
        for service in reversed(self.services):
            ret.update(service.get_all_format_tags())

        return ret

    def create_song(self, song: Song, group: str = ""):
        return self.services[0].create_song(song, group)

    def update_song_karaoke(self, song: Song):
        return self.services[0].update_song_karaoke(song)
