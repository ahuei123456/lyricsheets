from lyricsheets.effect.template_effect import retime
from lyricsheets.models.karaoke import KLine, KChar, KSyl
from unittest.mock import Mock
from datetime import timedelta
import pyass
import pytest


@pytest.fixture
def mock_kObjects():
    mock_kLine = Mock(spec=KLine)

    mock_kLine.start = timedelta(seconds=50)
    mock_kLine.end = timedelta(seconds=100)

    mock_kLine.syls = []
    for i in range(10):
        start = 50 + i * 5
        end = start + 5

        mock_kSyl = Mock(spec=KSyl)

        mock_kSyl.start = timedelta(seconds=i * 5)
        mock_kSyl.end = timedelta(seconds=(i + 1) * 5)
        mock_kSyl.duration = timedelta(seconds=5)

        mock_kSyl.chars = []

        for j in range(5):
            mock_kChar = Mock(spec=KChar)

            mock_kChar.start = mock_kSyl.start + timedelta(seconds=j)
            mock_kChar.end = mock_kChar.start + timedelta(seconds=1)
            mock_kChar.kSyl = mock_kSyl
            mock_kChar.kLine = mock_kLine
            mock_kChar.kChar = mock_kChar

            mock_kSyl.chars.append(mock_kChar)

        mock_kSyl.kLine = mock_kLine
        mock_kSyl.kSyl = mock_kSyl
        mock_kSyl.kChar = mock_kSyl.chars[0]

        mock_kLine.syls.append(mock_kSyl)

    mock_kLine.kLine = mock_kLine
    mock_kLine.kSyl = mock_kLine.syls[0]
    mock_kLine.kChar = mock_kLine.syls[0].chars[0]

    return {
        "line": mock_kLine,
        "syl": mock_kLine.syls[1],
        "char": mock_kLine.syls[1].chars[1],
    }


@pytest.fixture
def mock_event():
    mock_event = Mock(spec=pyass.Event)

    mock_event.start = timedelta(seconds=50)
    mock_event.end = timedelta(seconds=100)

    return mock_event


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        (
            "line",
            "abs",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
        (
            "line",
            "set",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
        (
            "syl",
            "abs",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
        (
            "syl",
            "set",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
        (
            "char",
            "abs",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
        (
            "char",
            "set",
            1000,
            2000,
            timedelta(milliseconds=1000),
            timedelta(milliseconds=2000),
        ),
    ],
)
def test_retime_abs_set(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]

    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "preline", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        ("line", "preline", -2000, -1000, timedelta(seconds=48), timedelta(seconds=49)),
        ("syl", "preline", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        ("syl", "preline", -2000, -1000, timedelta(seconds=48), timedelta(seconds=49)),
        ("char", "preline", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        ("char", "preline", -2000, -1000, timedelta(seconds=48), timedelta(seconds=49)),
    ],
)
def test_retime_preline(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "line", 1000, 2000, timedelta(seconds=51), timedelta(seconds=102)),
        ("line", "line", -2000, -1000, timedelta(seconds=48), timedelta(seconds=99)),
        ("syl", "line", 1000, 2000, timedelta(seconds=51), timedelta(seconds=102)),
        ("syl", "line", -2000, -1000, timedelta(seconds=48), timedelta(seconds=99)),
        ("char", "line", 1000, 2000, timedelta(seconds=51), timedelta(seconds=102)),
        ("char", "line", -2000, -1000, timedelta(seconds=48), timedelta(seconds=99)),
    ],
)
def test_retime_line(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "start2syl", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        (
            "line",
            "start2syl",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=49),
        ),
        ("syl", "start2syl", 1000, 2000, timedelta(seconds=51), timedelta(seconds=57)),
        (
            "syl",
            "start2syl",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=54),
        ),
        ("char", "start2syl", 1000, 2000, timedelta(seconds=51), timedelta(seconds=57)),
        (
            "char",
            "start2syl",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=54),
        ),
    ],
)
def test_retime_start2syl(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "presyl", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        ("line", "presyl", -2000, -1000, timedelta(seconds=48), timedelta(seconds=49)),
        ("syl", "presyl", 1000, 2000, timedelta(seconds=56), timedelta(seconds=57)),
        ("syl", "presyl", -2000, -1000, timedelta(seconds=53), timedelta(seconds=54)),
        ("char", "presyl", 1000, 2000, timedelta(seconds=56), timedelta(seconds=57)),
        ("char", "presyl", -2000, -1000, timedelta(seconds=53), timedelta(seconds=54)),
    ],
)
def test_retime_presyl(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "syl", 1000, 2000, timedelta(seconds=51), timedelta(seconds=57)),
        ("line", "syl", -2000, -1000, timedelta(seconds=48), timedelta(seconds=54)),
        ("syl", "syl", 1000, 2000, timedelta(seconds=56), timedelta(seconds=62)),
        ("syl", "syl", -2000, -1000, timedelta(seconds=53), timedelta(seconds=59)),
        ("char", "syl", 1000, 2000, timedelta(seconds=56), timedelta(seconds=62)),
        ("char", "syl", -2000, -1000, timedelta(seconds=53), timedelta(seconds=59)),
    ],
)
def test_retime_syl(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "postsyl", 1000, 2000, timedelta(seconds=56), timedelta(seconds=57)),
        ("line", "postsyl", -2000, -1000, timedelta(seconds=53), timedelta(seconds=54)),
        ("syl", "postsyl", 1000, 2000, timedelta(seconds=61), timedelta(seconds=62)),
        ("syl", "postsyl", -2000, -1000, timedelta(seconds=58), timedelta(seconds=59)),
        ("char", "postsyl", 1000, 2000, timedelta(seconds=61), timedelta(seconds=62)),
        ("char", "postsyl", -2000, -1000, timedelta(seconds=58), timedelta(seconds=59)),
    ],
)
def test_retime_postsyl(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "syl2end", 1000, 2000, timedelta(seconds=56), timedelta(seconds=102)),
        ("line", "syl2end", -2000, -1000, timedelta(seconds=53), timedelta(seconds=99)),
        ("syl", "syl2end", 1000, 2000, timedelta(seconds=61), timedelta(seconds=102)),
        ("syl", "syl2end", -2000, -1000, timedelta(seconds=58), timedelta(seconds=99)),
        ("char", "syl2end", 1000, 2000, timedelta(seconds=61), timedelta(seconds=102)),
        ("char", "syl2end", -2000, -1000, timedelta(seconds=58), timedelta(seconds=99)),
    ],
)
def test_retime_syl2end(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        (
            "line",
            "postline",
            1000,
            2000,
            timedelta(seconds=101),
            timedelta(seconds=102),
        ),
        (
            "line",
            "postline",
            -2000,
            -1000,
            timedelta(seconds=98),
            timedelta(seconds=99),
        ),
        ("syl", "postline", 1000, 2000, timedelta(seconds=101), timedelta(seconds=102)),
        ("syl", "postline", -2000, -1000, timedelta(seconds=98), timedelta(seconds=99)),
        (
            "char",
            "postline",
            1000,
            2000,
            timedelta(seconds=101),
            timedelta(seconds=102),
        ),
        (
            "char",
            "postline",
            -2000,
            -1000,
            timedelta(seconds=98),
            timedelta(seconds=99),
        ),
    ],
)
def test_retime_postline(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        (
            "line",
            "start2char",
            1000,
            2000,
            timedelta(seconds=51),
            timedelta(seconds=52),
        ),
        (
            "line",
            "start2char",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=49),
        ),
        ("syl", "start2char", 1000, 2000, timedelta(seconds=51), timedelta(seconds=57)),
        (
            "syl",
            "start2char",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=54),
        ),
        (
            "char",
            "start2char",
            1000,
            2000,
            timedelta(seconds=51),
            timedelta(seconds=58),
        ),
        (
            "char",
            "start2char",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=55),
        ),
    ],
)
def test_retime_start2char(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "prechar", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        ("line", "prechar", -2000, -1000, timedelta(seconds=48), timedelta(seconds=49)),
        ("syl", "prechar", 1000, 2000, timedelta(seconds=56), timedelta(seconds=57)),
        ("syl", "prechar", -2000, -1000, timedelta(seconds=53), timedelta(seconds=54)),
        ("char", "prechar", 1000, 2000, timedelta(seconds=57), timedelta(seconds=58)),
        ("char", "prechar", -2000, -1000, timedelta(seconds=54), timedelta(seconds=55)),
    ],
)
def test_retime_prechar(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "char", 1000, 2000, timedelta(seconds=51), timedelta(seconds=53)),
        ("line", "char", -2000, -1000, timedelta(seconds=48), timedelta(seconds=50)),
        ("syl", "char", 1000, 2000, timedelta(seconds=56), timedelta(seconds=58)),
        ("syl", "char", -2000, -1000, timedelta(seconds=53), timedelta(seconds=55)),
        ("char", "char", 1000, 2000, timedelta(seconds=57), timedelta(seconds=59)),
        ("char", "char", -2000, -1000, timedelta(seconds=54), timedelta(seconds=56)),
    ],
)
def test_retime_char(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "postchar", 1000, 2000, timedelta(seconds=52), timedelta(seconds=53)),
        (
            "line",
            "postchar",
            -2000,
            -1000,
            timedelta(seconds=49),
            timedelta(seconds=50),
        ),
        ("syl", "postchar", 1000, 2000, timedelta(seconds=57), timedelta(seconds=58)),
        ("syl", "postchar", -2000, -1000, timedelta(seconds=54), timedelta(seconds=55)),
        ("char", "postchar", 1000, 2000, timedelta(seconds=58), timedelta(seconds=59)),
        (
            "char",
            "postchar",
            -2000,
            -1000,
            timedelta(seconds=55),
            timedelta(seconds=56),
        ),
    ],
)
def test_retime_postchar(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "char2end", 1000, 2000, timedelta(seconds=52), timedelta(seconds=102)),
        (
            "line",
            "char2end",
            -2000,
            -1000,
            timedelta(seconds=49),
            timedelta(seconds=99),
        ),
        ("syl", "char2end", 1000, 2000, timedelta(seconds=57), timedelta(seconds=102)),
        ("syl", "char2end", -2000, -1000, timedelta(seconds=54), timedelta(seconds=99)),
        ("char", "char2end", 1000, 2000, timedelta(seconds=58), timedelta(seconds=102)),
        (
            "char",
            "char2end",
            -2000,
            -1000,
            timedelta(seconds=55),
            timedelta(seconds=99),
        ),
    ],
)
def test_retime_char2end(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "syl2char", 1000, 2000, timedelta(seconds=51), timedelta(seconds=52)),
        (
            "line",
            "syl2char",
            -2000,
            -1000,
            timedelta(seconds=48),
            timedelta(seconds=49),
        ),
        ("syl", "syl2char", 1000, 2000, timedelta(seconds=56), timedelta(seconds=57)),
        ("syl", "syl2char", -2000, -1000, timedelta(seconds=53), timedelta(seconds=54)),
        ("char", "syl2char", 1000, 2000, timedelta(seconds=56), timedelta(seconds=58)),
        (
            "char",
            "syl2char",
            -2000,
            -1000,
            timedelta(seconds=53),
            timedelta(seconds=55),
        ),
    ],
)
def test_retime_syl2char(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "char2syl", 1000, 2000, timedelta(seconds=52), timedelta(seconds=57)),
        (
            "line",
            "char2syl",
            -2000,
            -1000,
            timedelta(seconds=49),
            timedelta(seconds=54),
        ),
        ("syl", "char2syl", 1000, 2000, timedelta(seconds=57), timedelta(seconds=62)),
        ("syl", "char2syl", -2000, -1000, timedelta(seconds=54), timedelta(seconds=59)),
        ("char", "char2syl", 1000, 2000, timedelta(seconds=58), timedelta(seconds=62)),
        (
            "char",
            "char2syl",
            -2000,
            -1000,
            timedelta(seconds=55),
            timedelta(seconds=59),
        ),
    ],
)
def test_retime_char2syl(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta


@pytest.mark.parametrize(
    "type, mode, startadjust, endadjust, startdelta, enddelta",
    [
        ("line", "sylpct", 20, 80, timedelta(seconds=51), timedelta(seconds=59)),
        ("line", "sylpct", -80, -20, timedelta(seconds=46), timedelta(seconds=54)),
        ("syl", "sylpct", 20, 80, timedelta(seconds=56), timedelta(seconds=64)),
        ("syl", "sylpct", -80, -20, timedelta(seconds=51), timedelta(seconds=59)),
        ("char", "sylpct", 20, 80, timedelta(seconds=56), timedelta(seconds=64)),
        ("char", "sylpct", -80, -20, timedelta(seconds=51), timedelta(seconds=59)),
    ],
)
def test_retime_sylpct(
    mock_kObjects,
    mock_event,
    type: str,
    mode: str,
    startadjust: int,
    endadjust: int,
    startdelta: timedelta,
    enddelta: timedelta,
):
    mock_kObject = mock_kObjects[type]
    retime(mock_kObject, mock_event, mode, startadjust, endadjust)

    assert mock_event.start == startdelta
    assert mock_event.end == enddelta
