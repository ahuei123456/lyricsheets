# Lyricsheets

The project in which Google Sheets is both the frontend and the database. Generates advanced karaoke effects in `.ass` subtitle files.

## Overview

Lyricsheets takes song data (lyrics, syllable timings, metadata) stored in a Google Sheet and uses it to populate Aegisub (`.ass`) files. It generates timed karaoke lines, title cards, and allows for complex effects (KFX) and modifications directly from instructions within the `.ass` file itself.

## Prerequisites

*   **Python 3.14:** Ensure Python is installed and accessible from your command line. The repo pins Python 3.14 for uv.
*   **uv:** Install `uv` to create the project environment, run scripts, and build distributions.
*   **Aegisub:** You'll need Aegisub or a compatible `.ass` editor to prepare the initial timing file.
*   **Google Sheet:** A properly structured Google Sheet containing your song database (lyrics, timings, metadata).
*   **Google Cloud Credentials:** You'll need credentials set up to allow the script to access your Google Sheet via the API. 
*   **Dependencies:** Install required Python packages with uv:
    ```powershell
    uv sync
    ```

## Basic Usage

1.  **Prepare your Aegisub file:**
    *   Create an `.ass` file with basic karaoke timings for your song(s).
    *   For each song you want Lyricsheets to process, add a `Comment` line:
        *   Set the `Style` to `Song`.
        *   Set the `Start` time to the exact start time of the *first timed syllable* of the song.
        *   Set the `Text` field to the *exact title* of the song as it appears in your Google Sheet database.

    *Example `Song` comment line:*
    ```ass
    Comment: 0,0:03:19.27,0:03:19.27,Song,,0,0,0,,Mitaiken HORIZON 
    ```
    This line tells the script to find the song "Mitaiken HORIZON" in the database and start generating its lines based on the timing `0:03:19.27`.

2.  **Run the script:**
    Execute the `populate_songs.py` script, passing the `.ass` file(s) you prepared as arguments:

    ```powershell
    uv run lyricsheets-populate input.ass
    ```

    To process multiple files at once:
    ```powershell
    uv run lyricsheets-populate input1.ass input2.ass input3.ass ...
    ```

3.  **Output:**
    The script will modify the input `.ass` file(s) (or create new ones, depending on implementation) to include:
    *   A generated title card for the song.
    *   Timed Romaji lyric lines with basic effects.
    *   Timed English translation lines (if available) with basic effects.

## Command-Line Options

*   `--config <config_file_path>`: Specify the path to your configuration file (contains Google API credentials, Sheet ID, etc.). Defaults to `config.json` in the script's directory.
*   `--title <True/False>`: Control whether title cards are generated. Defaults to `True`.

## uv Commands

Run individual scripts through their installed command names:

```powershell
uv run lyricsheets-populate input.ass
uv run lyricsheets-create-song input.ass "Song Title"
uv run lyricsheets-edit-karaoke "Song Title"
uv run lyricsheets-print-karaoke "Song Title"
uv run lyricsheets-ass-to-modifier input.ass
```

You can still run the original script files directly:

```powershell
uv run python populate_songs.py input.ass
```

Build source and wheel distributions:

```powershell
uv build
```

## Local songs (no Google Sheets)

Songs can also be generated straight from a karaoke-timed `.ass` file instead of a spreadsheet, via a `local_songs` mapping in the config (`google_credentials` then becomes optional). See [the migration guide](.agents/skills/lua-to-python-kfx/reference.md), which covers porting existing Aegisub Lua karaoke templates to Python effects — it's also packaged as an [Agent Skill](https://agentskills.io) in [`.agents/skills/lua-to-python-kfx/`](.agents/skills/lua-to-python-kfx/) (auto-discovered by Codex, Gemini CLI, and other tools; Claude Code loads it via a shim in `.claude/skills/`).

## Advanced Features

For detailed information on customizing the output, applying advanced effects, and overriding database information, please refer to the project **Wiki**. Topics include:

*   **Modifiers:** Fine-tune line generation (discarding, offsetting, styling, etc.) directly within the `Song` comment line.
*   **Effects (KFX):** Apply complex, script-based karaoke effects.
*   **Detailed Configuration:** Explanation of the `config.json` file.
*   **Google Sheet Setup:** How to structure your database sheet.

## Contributing

*(Add contribution guidelines here if applicable)*

## License

*(Add license information here)*
