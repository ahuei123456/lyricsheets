from pathlib import Path
from typing import Annotated

import typer

from convert_ass_to_karaoke_modifier import (
    convert_ass_to_karaoke_modifier as convert_ass_to_karaoke_modifier_script,
)
from create_song import create_song as create_song_script
from edit_song_karaoke import edit_song_karaoke as edit_song_karaoke_script
from populate_songs import populate_song_files
from print_song_karaoke import print_song_karaoke as print_song_karaoke_script

DEFAULT_EFFECT = "default_live_karaoke_effect"

app = typer.Typer(
    help="Generate karaoke subtitle effects from Google Sheets song data.",
    no_args_is_help=True,
)


@app.command("populate_songs")
def populate_songs_command(
    input_fnames: Annotated[list[Path], typer.Argument(help="Path to input files")],
    title: Annotated[
        bool, typer.Option("--title/--no-title", help="Whether to print the title")
    ] = True,
    config: Annotated[
        Path, typer.Option("--config", help="Path to config file")
    ] = Path("./config.json"),
    effect: Annotated[
        str, typer.Option("--effect", help="Default effect to use")
    ] = DEFAULT_EFFECT,
    force_effect: Annotated[
        str,
        typer.Option(
            "--force-effect",
            help="Force overwrite effect even if an effect is specified in kfx tags",
        ),
    ] = "",
) -> None:
    if force_effect and effect != DEFAULT_EFFECT:
        raise typer.BadParameter("--effect and --force-effect are mutually exclusive")

    populate_song_files(input_fnames, title, config, effect, force_effect)


@app.command("create_song")
def create_song_command(
    input_fname: Annotated[Path, typer.Argument(help="Path to input file")],
    title: Annotated[str, typer.Argument(help="Title of the song")],
    group: Annotated[
        str | None, typer.Option("--group", help="Group that sang the song")
    ] = None,
    config: Annotated[
        Path, typer.Option("--config", help="Path to config file")
    ] = Path("./config.json"),
) -> None:
    create_song_script(input_fname, title, group, config)


@app.command("edit_song_karaoke")
def edit_song_karaoke_command(
    title: Annotated[str, typer.Argument(help="Title of the song")],
    group: Annotated[
        str | None, typer.Option("--group", help="Group that sang the song")
    ] = None,
    config: Annotated[
        Path, typer.Option("--config", help="Path to config file")
    ] = Path("./config.json"),
) -> None:
    edit_song_karaoke_script(title, group, config)


@app.command("print_song_karaoke")
def print_song_karaoke_command(
    song_name: Annotated[str, typer.Argument(help="Title of the song")],
    line_nums: Annotated[
        list[int] | None,
        typer.Option(
            "--line-nums",
            help="Line numbers to print. Repeat the option for multiple lines.",
        ),
    ] = None,
    config: Annotated[
        Path, typer.Option("--config", help="Path to config file")
    ] = Path("./config.json"),
) -> None:
    print_song_karaoke_script(song_name, line_nums, config)


@app.command("convert_ass_to_karaoke_modifier")
def convert_ass_to_karaoke_modifier_command(
    input_fname: Annotated[Path, typer.Argument(help="Path to input file")],
    offset: Annotated[int, typer.Option("--offset", help="Index of first line")] = 1,
) -> None:
    convert_ass_to_karaoke_modifier_script(input_fname, offset)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
