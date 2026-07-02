import argparse
import json
import os
import pyass

from lyricsheets.ass import read_karaoke
from lyricsheets.models import Song, SongTitle
from lyricsheets.service import SongServiceByDB


def create_song(input_fname, title, group=None, config="./config.json"):
    if not os.path.isfile(input_fname):
        raise Exception(f"{input_fname} is not a file")

    with open(config) as f:
        config = json.load(f)

    with open(input_fname, encoding="utf_8_sig") as f:
        rawFile = pyass.load(f)

        song = Song(
            title=SongTitle(romaji=title),
            lyrics=read_karaoke(rawFile.events),
        )

    songService = SongServiceByDB(
        config["google_credentials"],
        config["spreadsheets"],
        config["default"],
    )

    songService.create_song(song, group)


def main():
    parser = argparse.ArgumentParser(
        description="Reads karaoke timing from an .ass file and uploads it to Google Sheets"
    )

    parser.add_argument("input_fname", help="Path to input file")
    parser.add_argument("title", help="Title of the song")
    parser.add_argument("--group", help="Group that sang the song")
    parser.add_argument("--config", help="Path to config file", default="./config.json")

    args = parser.parse_args()
    create_song(args.input_fname, args.title, args.group, args.config)


if __name__ == "__main__":
    main()
