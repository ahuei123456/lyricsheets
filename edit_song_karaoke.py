import argparse
import json
import os
import platform
import subprocess
import tempfile
import pyass

from lyricsheets.ass import read_karaoke
from lyricsheets.cache import MemoryCache
from lyricsheets.effect import KaraokeOnlyEffect
from lyricsheets.service import SongServiceByDB


def edit_song_karaoke(title, group=None, config="./config.json"):
    with open(config) as f:
        config = json.load(f)

    songService = SongServiceByDB(
        config["google_credentials"],
        config["spreadsheets"],
        config["default"],
        MemoryCache(),
    )

    print("Fetching song...")
    song = songService.get_song(title)
    script = pyass.Script(
        styles=[pyass.Style()], events=KaraokeOnlyEffect().to_events(song, {}, False)
    )

    print("Creating temporary file...")
    f = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf_8_sig", suffix=".ass", delete=False
    )
    pyass.dump(script, f)
    f.close()

    fileNameForAegisub = f.name
    if "microsoft-standard-WSL" in platform.uname().release:
        out = subprocess.run(
            ["wslpath", "-w", f.name], capture_output=True, check=True, text=True
        )
        fileNameForAegisub = out.stdout

    print("Waiting for file to be closed...")
    subprocess.run(
        ["powershell.exe", "-command", "start", "-Wait", fileNameForAegisub], check=True
    )
    print("File closed")

    with open(f.name, encoding="utf_8_sig") as f:
        song.lyrics = read_karaoke(pyass.load(f).events)
        songService.update_song_karaoke(song)

    os.remove(f.name)


def main():
    parser = argparse.ArgumentParser(
        description="Edits karaoke timing and updates it Google Sheets"
    )

    parser.add_argument("title", help="Title of the song")
    parser.add_argument("--group", help="Group that sang the song")
    parser.add_argument("--config", help="Path to config file", default="./config.json")

    args = parser.parse_args()
    edit_song_karaoke(args.title, args.group, args.config)


if __name__ == "__main__":
    main()
