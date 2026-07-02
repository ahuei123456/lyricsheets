from lyricsheets.effect.template_effect import TemplateEffect

import pytest


help = 4


def try3(a, b) -> int:
    return 12


def try4(a, b, num: int) -> int:
    return num + 1


@pytest.mark.parametrize(
    "text, data",
    [
        ("3+5", 8),
        ("(1+4)*3", 15),
        ("help+14", 18),
        ("try3()*3+10", 46),
        ("try4(help)+1", 6),
    ],
)
def test_template_function_eval(text: str, data):
    fndata = TemplateEffect._evaluate_expression(text, None, None, globals())
    assert fndata == data
