from collections.abc import Mapping
import os
import string
from typing import Any, Optional, Union

import pyass

from lyricsheets.ass.from_ass import read_karaoke
from lyricsheets.models import Song, SongTitle

from .service import SongService, NotFoundError

KARAOKE_EFFECT = "karaoke"


def to_song_key(songName: str) -> str:
    return "".join(
        "" if c in string.punctuation or c in string.whitespace else c
        for c in songName.encode("ascii", "ignore").decode().lower()
    )


def _is_karaoke_source_event(event: pyass.Event) -> bool:
    # Both Dialogue and Comment events are accepted so the source lines can be
    # commented out in the file without affecting playback.
    return KARAOKE_EFFECT in event.effect.lower() and event.text != ""


def _matches_style(styleName: str, explicitPrefix: Optional[str], hint: str) -> bool:
    if explicitPrefix is not None:
        return styleName.startswith(explicitPrefix)

    return hint in styleName.lower()


def _parse_actor(event: pyass.Event) -> tuple[str, bool]:
    # An actor like "blue 2" means actor "blue" on a secondary (backing vocal) line
    tokens = event.name.split()
    isSecondary = "2" in tokens
    actor = " ".join(token for token in tokens if token != "2")

    return actor, isSecondary or event.style.rstrip().endswith("2")


def song_from_ass(
    path: str,
    title: str = "",
    romajiStylePrefix: Optional[str] = None,
    enStylePrefix: Optional[str] = None,
) -> Song:
    """Build a Song from a karaoke-timed .ass file instead of a Google Sheets DB.

    Reads events (Dialogue or Comment) whose Effect contains "karaoke":
    - Romaji lines (style matching `romajiStylePrefix`, or containing "romaji")
      must carry {\\k} syllable timings.
    - English lines (style matching `enStylePrefix`, or containing "english")
      are paired with romaji lines in file order and provide the translation.
    - The Name (actor) field provides the line's actor; a "2" token or a style
      name ending in "2" marks the line as secondary.
    """
    with open(path, encoding="utf_8_sig") as f:
        doc = pyass.load(f)

    romajiEvents: list[pyass.Event] = []
    enEvents: list[pyass.Event] = []

    for event in doc.events:
        if not _is_karaoke_source_event(event):
            continue

        if _matches_style(event.style, romajiStylePrefix, "romaji"):
            romajiEvents.append(event)
        elif _matches_style(event.style, enStylePrefix, "english"):
            enEvents.append(event)

    if not romajiEvents:
        raise ValueError(f"{path}: no karaoke-timed romaji events found")

    if enEvents and len(enEvents) != len(romajiEvents):
        raise ValueError(
            f"{path}: {len(romajiEvents)} romaji events but {len(enEvents)} English events; "
            "they must pair up 1:1 in file order"
        )

    lines = read_karaoke(romajiEvents)

    for i, (line, event) in enumerate(zip(lines, romajiEvents)):
        actor, isSecondary = _parse_actor(event)

        line.idxInSong = i + 1
        line.actors = [actor]
        line.breakpoints = [0]
        line.isSecondary = isSecondary

        if enEvents:
            line.en = enEvents[i].text

    return Song(
        title=SongTitle(romaji=title),
        lyrics=lines,
    )


class SongServiceByAssFiles(SongService):
    """SongService backed by local karaoke-timed .ass files.

    `songs` maps song titles to either a path, or a mapping:
        {"path": ..., "romaji_style": <style name prefix>, "en_style": <style name prefix>}
    Relative paths are resolved against `baseDir`.
    """

    def __init__(
        self,
        songs: Mapping[str, Union[str, Mapping[str, Any]]],
        baseDir: str = "",
    ) -> None:
        self.songConfigs = {}

        for name, songConfig in songs.items():
            if isinstance(songConfig, str):
                songConfig = {"path": songConfig}

            path = songConfig["path"]
            if baseDir and not os.path.isabs(path):
                path = os.path.join(baseDir, path)

            self.songConfigs[to_song_key(name)] = {
                "title": name,
                "path": path,
                "romajiStylePrefix": songConfig.get("romaji_style"),
                "enStylePrefix": songConfig.get("en_style"),
            }

    def get_song(self, songName: str) -> Song:
        songKey = to_song_key(songName)
        if songKey not in self.songConfigs:
            raise NotFoundError(songName)

        songConfig = self.songConfigs[songKey]
        return song_from_ass(
            songConfig["path"],
            title=songConfig["title"],
            romajiStylePrefix=songConfig["romajiStylePrefix"],
            enStylePrefix=songConfig["enStylePrefix"],
        )

    def get_format_tags(self, group: str = "") -> Mapping[str, str]:
        return {}

    def get_all_format_tags(self) -> Mapping[str, str]:
        return {}

    def create_song(self, song: Song, group: str = ""):
        raise NotImplementedError("SongServiceByAssFiles is read-only")

    def update_song_karaoke(self, song: Song):
        raise NotImplementedError("SongServiceByAssFiles is read-only")
