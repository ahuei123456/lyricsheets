import argparse
import json

from lyricsheets.cache import MemoryCache
from lyricsheets.service import SongServiceByDB


def print_song_karaoke(song_name, line_nums=None, config="./config.json"):
    with open(config) as f:
        config = json.load(f)

    songService = SongServiceByDB(
        config["google_credentials"],
        config["spreadsheets"],
        config["default"],
        MemoryCache(),
    )

    song = songService.get_song(song_name)
    for i, line in enumerate(song.lyrics):
        if not line_nums or i + 1 in line_nums:
            print("|".join([syllable.text for syllable in line.syllables]))


def main():
    parser = argparse.ArgumentParser(
        description="Prints the romaji lines of a song to be used as input into the karaoke timing app"
    )
    parser.add_argument("song_name")
    parser.add_argument("--line-nums", nargs="*", type=int)
    parser.add_argument("--config", help="Path to config file", default="./config.json")

    args = parser.parse_args()
    print_song_karaoke(args.song_name, args.line_nums, args.config)


if __name__ == "__main__":
    main()
