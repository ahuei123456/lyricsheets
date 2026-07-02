from collections.abc import Mapping, Sequence
from datetime import timedelta
import functools
import itertools
import operator
from typing import Optional, Any

from lyricsheets.cache import Cache, with_cache
from lyricsheets.models import *
from lyricsheets.sheets import GoogleSheetsClient, RateLimitedGoogleSheetsClient


class SongTemplateDB:
    TEMPLATE_SHEET_NAME = "Template"

    def __init__(
        self,
        googleCredentials: Mapping[str, str],
        client: Optional[GoogleSheetsClient] = None,
        cache: Optional[Cache] = None,
    ) -> None:
        if client is not None:
            self.sheetsClient = client
        else:
            self.sheetsClient = RateLimitedGoogleSheetsClient(googleCredentials)

        self.cache = cache

    @with_cache("SongTemplateDB::get_sheet_name_to_id_map")
    def get_sheet_name_to_id_map(self, spreadsheetId: str) -> Mapping[str, int]:
        resp = self.sheetsClient.get(
            spreadsheetId,
            fields="sheets.properties",
        )

        return {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in resp["sheets"]
        }

    @with_cache("SongTemplateDB::get_format_map")
    def get_format_map(self, spreadsheetId: str) -> Mapping[str, Any]:
        rootPos = "I1"
        rootPosRow = self.sheetsClient.get_row("I1") + 1

        resp = self.sheetsClient.get(
            spreadsheetId,
            ranges=f"{SongTemplateDB.TEMPLATE_SHEET_NAME}!{rootPos}:{rootPosRow}",
            fields="sheets.data.rowData.values(userEnteredValue,userEnteredFormat(backgroundColor,textFormat.foregroundColor))",
        )

        return {
            resp["sheets"][0]["data"][0]["rowData"][1]["values"][i - 1][
                "userEnteredValue"
            ]["stringValue"]: v["userEnteredFormat"]
            for i, v in enumerate(resp["sheets"][0]["data"][0]["rowData"][0]["values"])
            if "userEnteredFormat" in v
            and "userEnteredValue" in v
            and not self.sheetsClient.is_white(
                v["userEnteredFormat"]["backgroundColor"]
            )
        }

    @with_cache("SongTemplateDB::get_format_tags")
    def get_format_tags(self, spreadsheetId: str) -> Mapping[str, str]:
        rootPos = "I1"
        row = self.sheetsClient.get_row(rootPos) + 1

        resp = self.sheetsClient.get(
            spreadsheetId,
            ranges=f"{SongTemplateDB.TEMPLATE_SHEET_NAME}!{rootPos}:{row}",
            fields="sheets.data.rowData.values.userEnteredValue",
        )

        respIter0 = iter(resp["sheets"][0]["data"][0]["rowData"][0]["values"])
        respIter1 = iter(resp["sheets"][0]["data"][0]["rowData"][1]["values"])

        return {
            formatKey["userEnteredValue"]["stringValue"]: formatStr["userEnteredValue"][
                "stringValue"
            ]
            for formatStr, formatKey in zip(respIter0, respIter1)
            if "userEnteredValue" in formatStr and "userEnteredValue" in formatKey
        }


class SongDB:
    def __init__(
        self,
        googleCredentials: Mapping[str, str],
        client: Optional[GoogleSheetsClient] = None,
        cache: Optional[Cache] = None,
    ) -> None:
        if client is not None:
            self.sheetsClient = client
        else:
            self.sheetsClient = RateLimitedGoogleSheetsClient(googleCredentials)

        self.songTemplateDB = SongTemplateDB(
            googleCredentials, self.sheetsClient, cache
        )
        self.cache = cache

    @with_cache("SongDB::list_song_names")
    def list_song_names(self, spreadsheetId: str) -> Sequence[str]:
        return list(self.songTemplateDB.get_sheet_name_to_id_map(spreadsheetId).keys())

    @with_cache("SongDB::get_song")
    def get_song(self, spreadsheetId: str, songName: str) -> song.Song:
        return self._parse_song(
            spreadsheetId, self._get_song_data(spreadsheetId, songName)
        )

    def _get_song_data(self, spreadsheetId: str, songName: str):
        resp = self.sheetsClient.get(
            spreadsheetId,
            ranges=[f"'{songName}'"],
            fields="sheets.data.rowData.values(formattedValue,userEnteredFormat(backgroundColor,textFormat.foregroundColor))",
        )
        return resp["sheets"][0]["data"][0]["rowData"]

    def _parse_song(self, spreadsheetId: str, sheetData) -> song.Song:
        return song.Song(
            title=self._parse_title(sheetData),
            creators=self._parse_creators(sheetData),
            lyrics=list(self._parse_lyrics(spreadsheetId, sheetData)),
        )

    def _parse_title(self, sheetData) -> song.SongTitle:
        col = self.sheetsClient.get_column_idx("B")
        ret = song.SongTitle(romaji=sheetData[0]["values"][col]["formattedValue"])

        if "formattedValue" in sheetData[1]["values"][col]:
            ret.en = sheetData[1]["values"][col]["formattedValue"]

        return ret

    def _parse_creators(self, sheetData) -> song.SongCreators:
        col = self.sheetsClient.get_column_idx("E")
        try:
            artist = sheetData[0]["values"][col]["formattedValue"].strip()
        except KeyError:
            artist = ""

        return song.SongCreators(
            artist=artist,
            composers=self._parse_creator(sheetData, 1, col),
            arrangers=self._parse_creator(sheetData, 2, col),
            writers=self._parse_creator(sheetData, 3, col),
        )

    def _parse_creator(self, sheetData, row: int, col: int) -> list[str]:
        try:
            return [
                creator.strip()
                for creator in sheetData[row]["values"][col]["formattedValue"].split(
                    ","
                )
            ]
        except (IndexError, KeyError):  # fmt: skip
            return []

    def _parse_lyrics(self, spreadsheetId: str, sheetData) -> Sequence[song.SongLine]:
        colorToActorMap = {
            self.sheetsClient.color_to_hex(format["backgroundColor"]): actor
            for actor, format in self.songTemplateDB.get_format_map(
                spreadsheetId
            ).items()
        }

        return [
            self._parse_line(line, colorToActorMap)
            for line in itertools.islice(sheetData, 5, None, 1)
            if "values" in line and "formattedValue" in line["values"][0]
        ]

    def _parse_line(
        self, rowData: Mapping[str, Any], colorToActorMap: Mapping[str, str]
    ) -> song.SongLine:
        values = rowData["values"]
        timeAndSyllables = [
            syllable
            for syllable in values[self.sheetsClient.get_column_idx("I") :]
            if "formattedValue" in syllable
            or (
                "userEnteredFormat" in syllable
                and not self.sheetsClient.is_white(
                    syllable["userEnteredFormat"]["backgroundColor"]
                )
            )
        ]

        syllables: list[song.SongLineSyllable] = []
        actors: list[str] = []
        breakpoints: list[int] = []

        timeAndSyllablesIter = iter(timeAndSyllables)
        for i, (val1, val2) in enumerate(
            zip(timeAndSyllablesIter, timeAndSyllablesIter)
        ):
            syllables.append(
                song.SongLineSyllable(
                    timedelta(milliseconds=int(val1["formattedValue"]) * 10),
                    val2.get("formattedValue", ""),
                )
            )

            currActor = colorToActorMap[
                self.sheetsClient.color_to_hex(
                    val2["userEnteredFormat"]["backgroundColor"]
                )
            ]
            if not actors or currActor != actors[-1]:
                actors.append(currActor)
                breakpoints.append(i)

        return song.SongLine(
            idxInSong=int(
                values[self.sheetsClient.get_column_idx("A")].get("formattedValue", "")
            ),
            en=values[self.sheetsClient.get_column_idx("B")].get("formattedValue", ""),
            isSecondary="formattedValue"
            in values[self.sheetsClient.get_column_idx("F")],
            start=self._parse_timedelta(
                values[self.sheetsClient.get_column_idx("G")]["formattedValue"]
            ),
            end=self._parse_timedelta(
                values[self.sheetsClient.get_column_idx("H")]["formattedValue"]
            ),
            syllables=syllables,
            actors=actors,
            breakpoints=breakpoints,
        )

    def _parse_timedelta(self, tdStr: str) -> timedelta:
        sStr, _, csStr = tdStr.partition(".")
        hrs, mins, secs = map(int, sStr.split(":"))
        cs = int(csStr)

        return timedelta(hours=hrs, minutes=mins, seconds=secs, milliseconds=cs * 10)

    def create_song(self, spreadsheetId: str, song: Song):
        self._create_song_sheet(spreadsheetId, song.title)

        self._create_title(spreadsheetId, song.title.romaji, song.title)
        self._create_creators(spreadsheetId, song.title.romaji, song.creators)
        self._create_english(spreadsheetId, song.title.romaji, song.lyrics)
        self._create_is_secondary(spreadsheetId, song.title.romaji, song.lyrics)
        self._create_line_times(spreadsheetId, song.title.romaji, song.lyrics)
        self._create_line_karaoke(spreadsheetId, song.title.romaji, song.lyrics)
        self._create_romaji(spreadsheetId, song.title.romaji, song.lyrics)
        self._create_line_actors(spreadsheetId, song.title.romaji, song.lyrics)

    def _create_song_sheet(self, spreadsheetId: str, songTitle: SongTitle):
        sheetNameToId = self.songTemplateDB.get_sheet_name_to_id_map(spreadsheetId)

        self.sheetsClient.batch_update(
            spreadsheetId,
            [
                {
                    "duplicateSheet": {
                        "sourceSheetId": sheetNameToId[
                            self.songTemplateDB.TEMPLATE_SHEET_NAME
                        ],
                        # Template sheet should be the last sheet
                        "insertSheetIndex": len(sheetNameToId) - 1,
                        "newSheetName": songTitle.romaji,
                    }
                }
            ],
        )

    def _create_title(self, spreadsheetId: str, sheetName: str, songTitle: SongTitle):
        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!B1",
            values=[
                [songTitle.romaji],
                [songTitle.en if songTitle.en else ""],
            ],
        )

    def _create_creators(
        self, spreadsheetId: str, sheetName: str, songCreators: SongCreators
    ):
        if songCreators == SongCreators():
            return

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!E1",
            values=[
                [songCreators.artist],
                [", ".join(songCreators.composers)],
                [", ".join(songCreators.arrangers)],
                [", ".join(songCreators.writers)],
            ],
        )

    def _create_english(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        if len([line.en for line in songLines if line.en != ""]) == 0:
            return

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!B6",
            values=[[line.en] for line in songLines],
        )

    def _create_is_secondary(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        if len([line.isSecondary for line in songLines if line.isSecondary]) == 0:
            return

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!F6",
            values=[["U"] if line.isSecondary else [] for line in songLines],
        )

    def _create_line_times(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        if (
            len(
                [
                    (line.start, line.end)
                    for line in songLines
                    if line.start != timedelta() and line.end != timedelta
                ]
            )
            == 0
        ):
            return

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!G6",
            values=[
                [self._format_timedelta(line.start), self._format_timedelta(line.end)]
                for line in songLines
            ],
        )

    def _create_line_karaoke(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        if all([len(line.syllables) == 0 for line in songLines]):
            return

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!I6",
            values=[
                functools.reduce(
                    operator.iconcat,
                    [
                        [
                            int(syllable.length.total_seconds() * 100),
                            syllable.text,
                        ]
                        for syllable in line.syllables
                    ],
                    [],
                )
                for line in songLines
            ],
        )

    def _create_line_actors(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        if all([len(line.actors) == 0 for line in songLines]):
            return

        rootPos = "I6"

        sheetId = self.songTemplateDB.get_sheet_name_to_id_map(spreadsheetId)[sheetName]
        rowOffset = self.sheetsClient.get_row_idx(rootPos)
        columnOffset = self.sheetsClient.get_column_idx(rootPos)

        formatMap = self.songTemplateDB.get_format_map(spreadsheetId)

        requests = []
        for lineIdx, line in enumerate(songLines):
            for i in range(len(line.actors)):
                actor = line.actors[i]
                startIdx = line.breakpoints[i]
                endIdx = (
                    len(line.syllables)
                    if i == len(line.actors) - 1
                    else line.breakpoints[i + 1]
                )

                req = {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheetId,
                            "startRowIndex": rowOffset + lineIdx,
                            "endRowIndex": rowOffset + lineIdx + 1,
                            "startColumnIndex": columnOffset + startIdx * 2,
                            "endColumnIndex": columnOffset + endIdx * 2,
                        },
                        "cell": {"userEnteredFormat": formatMap[actor]},
                        "fields": "userEnteredFormat(backgroundColor,textFormat.foregroundColor)",
                    }
                }

                requests.append(req)

        self.sheetsClient.batch_update(spreadsheetId, requests=requests)

    def _create_romaji(
        self, spreadsheetId: str, sheetName: str, songLines: Sequence[SongLine]
    ):
        rootPos = "E6"
        r = self.sheetsClient.get_row(rootPos)

        self.sheetsClient.append_values(
            spreadsheetId,
            range=f"{sheetName}!{rootPos}",
            values=[
                [
                    f'=CONCATENATE(ARRAYFORMULA(IF(MOD(COLUMN(I{r + i}:{r + i}),2)=MOD(COLUMN(I{r + i}),2), "", I{r + i}:{r + i})))'
                ]
                for i in range(len(songLines))
            ],
            valueInputOption=GoogleSheetsClient.ValueInputOption.USER_ENTERED,
        )

    def update_song_karaoke(self, spreadsheetId: str, newSong: Song):
        if len(newSong.lyrics) == 0:
            return []

        sheetName = newSong.title.romaji
        oldSongData = self._get_song_data(spreadsheetId, sheetName)
        oldSong = self._parse_song(spreadsheetId, oldSongData)

        if len(oldSong.lyrics) != len(newSong.lyrics):
            raise NotImplementedError("Number of lines do not match")

        sheetId = self.songTemplateDB.get_sheet_name_to_id_map(spreadsheetId)[sheetName]
        lineIdxToRowIdx = self._get_line_idx_to_row_idx_map(oldSongData)
        formatMap = self.songTemplateDB.get_format_map(spreadsheetId)

        requests = [
            *self._get_update_line_times_requests(
                sheetId, lineIdxToRowIdx, oldSong.lyrics, newSong.lyrics
            ),
            *self._get_update_line_karaoke_requests(
                sheetId, lineIdxToRowIdx, formatMap, oldSong.lyrics, newSong.lyrics
            ),
        ]

        if len(requests) > 0:
            self.sheetsClient.batch_update(spreadsheetId, requests)

            if self.cache is not None:
                self.cache.delete(f"SongDB::get_song:{spreadsheetId}:{sheetName}")

    def _get_update_line_times_requests(
        self,
        sheetId: int,
        lineIdxToRowIdx: Sequence[int],
        oldSongLines: Sequence[SongLine],
        newSongLines: Sequence[SongLine],
    ) -> Sequence[Mapping[str, Any]]:
        requests = []
        for idx, (oldLine, newLine) in enumerate(zip(oldSongLines, newSongLines)):
            if oldLine.start != newLine.start:
                requests.append(
                    self._get_update_cell_value_request(
                        sheetId,
                        lineIdxToRowIdx[idx],
                        self.sheetsClient.get_column_idx("G"),
                        {"stringValue": self._format_timedelta(newLine.start)},
                    )
                )
            if oldLine.end != newLine.end:
                requests.append(
                    self._get_update_cell_value_request(
                        sheetId,
                        lineIdxToRowIdx[idx],
                        self.sheetsClient.get_column_idx("H"),
                        {"stringValue": self._format_timedelta(newLine.end)},
                    )
                )

        return requests

    def _get_update_line_karaoke_requests(
        self,
        sheetId: int,
        lineIdxToRowIdx: Sequence[int],
        formatMap: Mapping[str, Any],
        oldSongLines: Sequence[SongLine],
        newSongLines: Sequence[SongLine],
    ) -> Sequence[Mapping[str, Any]]:
        requests = []
        for lineIdx, (oldLine, newLine) in enumerate(zip(oldSongLines, newSongLines)):
            if oldLine.romaji != newLine.romaji:
                raise NotImplementedError(f"Line {lineIdx + 1} romaji does not match")

            if oldLine.syllables == newLine.syllables:
                continue

            # Derive the actor for each char in the old line
            oldLine.breakpoints.append(len(oldLine.syllables))
            oldSyllableToActor = []
            for i in range(len(oldLine.breakpoints) - 1):
                numSyllables = oldLine.breakpoints[i + 1] - oldLine.breakpoints[i]
                oldSyllableToActor.extend(
                    [oldLine.actors[i] for _ in range(numSyllables)]
                )

            charToActor = []
            for actor, newSyllable in zip(oldSyllableToActor, oldLine.syllables):
                charToActor.extend([actor for _ in range(len(newSyllable.text))])

            # Use the actor of each char to try to derive a unique actor for each new syllable
            # Fail if this cannot be done
            newSyllableToActor = []
            currCharIdx = 0
            for newSyllable in newLine.syllables:
                # If the syllable is empty, take the actor of the last syllable
                if newSyllable.text == "":
                    newSyllableToActor.append(charToActor[currCharIdx - 1])
                else:
                    actors = set(
                        charToActor[currCharIdx : currCharIdx + len(newSyllable.text)]
                    )

                    if len(actors) != 1:
                        raise NotImplementedError(
                            f"Syllable '{newSyllable.text}' in line {lineIdx + 1} does not have a unique actor, actors: {actors}"
                        )

                    newSyllableToActor.append(list(actors)[0])
                    currCharIdx += len(newSyllable.text)

            for syllableIdx, (
                oldSyllable,
                oldActor,
                newSyllable,
                newActor,
            ) in enumerate(
                itertools.zip_longest(
                    oldLine.syllables,
                    oldSyllableToActor,
                    newLine.syllables,
                    newSyllableToActor,
                )
            ):
                if newSyllable is None:
                    # Old line had more syllables, blank out the extra cells
                    requests.append(
                        self._get_clear_cell_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("I") + 2 * syllableIdx,
                        )
                    )
                    requests.append(
                        self._get_clear_cell_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("J") + 2 * syllableIdx,
                        )
                    )
                    continue

                if oldSyllable is None or oldSyllable.length != newSyllable.length:
                    requests.append(
                        self._get_update_cell_value_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("I") + 2 * syllableIdx,
                            {
                                "numberValue": int(
                                    newSyllable.length.total_seconds() * 100
                                )
                            },
                        )
                    )

                if oldSyllable is None or oldSyllable.text != newSyllable.text:
                    requests.append(
                        self._get_update_cell_value_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("J") + 2 * syllableIdx,
                            {"stringValue": newSyllable.text},
                        )
                    )

                if oldSyllable is None or oldActor != newActor:
                    requests.append(
                        self._get_update_cell_format_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("I") + 2 * syllableIdx,
                            formatMap[newActor],
                        )
                    )

                    requests.append(
                        self._get_update_cell_format_request(
                            sheetId,
                            lineIdxToRowIdx[lineIdx],
                            self.sheetsClient.get_column_idx("J") + 2 * syllableIdx,
                            formatMap[newActor],
                        )
                    )

        return requests

    def _get_update_cell_value_request(
        self, sheetId: int, rowIdx: int, colIdx: int, userEnteredValue: dict[str, Any]
    ) -> Mapping[str, Any]:
        return {
            "updateCells": {
                "rows": [{"values": [{"userEnteredValue": userEnteredValue}]}],
                "fields": "userEnteredValue",
                "start": {
                    "sheetId": sheetId,
                    "rowIndex": rowIdx,
                    "columnIndex": colIdx,
                },
            }
        }

    def _get_update_cell_format_request(
        self, sheetId: int, rowIdx: int, colIdx: int, userEnteredFormat: dict[str, Any]
    ) -> Mapping[str, Any]:
        return {
            "updateCells": {
                "rows": [{"values": [{"userEnteredFormat": userEnteredFormat}]}],
                "fields": "userEnteredFormat(backgroundColor,textFormat.foregroundColor)",
                "start": {
                    "sheetId": sheetId,
                    "rowIndex": rowIdx,
                    "columnIndex": colIdx,
                },
            }
        }

    def _get_clear_cell_request(
        self,
        sheetId: int,
        rowIdx: int,
        colIdx: int,
    ) -> Mapping[str, Any]:
        return {
            "updateCells": {
                "rows": [
                    {"values": [{"userEnteredValue": {}, "userEnteredFormat": {}}]}
                ],
                "fields": "userEnteredValue,userEnteredFormat(backgroundColor,textFormat.foregroundColor)",
                "start": {
                    "sheetId": sheetId,
                    "rowIndex": rowIdx,
                    "columnIndex": colIdx,
                },
            }
        }

    def _get_line_idx_to_row_idx_map(self, sheetData) -> Sequence[int]:
        ret = []

        for row in range(5, len(sheetData)):
            if (
                "values" in sheetData[row]
                and "formattedValue" in sheetData[row]["values"][0]
            ):
                ret.append(row)

        return ret

    def _format_timedelta(self, td: timedelta) -> str:
        hours, remainder = td.total_seconds() // 3600, td.total_seconds() % 3600
        minutes, seconds = remainder // 60, remainder % 60

        return "{:01}:{:02}:{:02}.{:02}".format(
            int(hours), int(minutes), int(seconds), int(td.microseconds // 10000)
        )
