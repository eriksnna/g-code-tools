import pytest

from core.expander import expand_program
from core.lexer import ERROR

USER_PROGRAM = """
G01
F400

G90
Y0
X0
G91

#1=2.8 (incremento X - step per dot)
#2=6 (attesa dopo arc start)
#3=2 (attesa dopo arc stop)
#4=20 (numero dot)
#5=5 (Incremento Z fra layer)
#6=8 (numero strati)
#7=60 (tempo di attesa tra strati)

M98 P1000 L#6  (si ripete L#6 volte)
G91
Z20
M30

O1000 (strati)
M98 P2000 L#4  (si ripete L#4 volte)
G91
Z#5
G90
X0
G91 G01
G04 P#7      (idle time pause)
M99  (return to main program)

O2000 (cordoni dot by dot)
M08          (arc start)
G04 P#2      (attesa dopo arc start)
M09          (arc stop)
G04 P#3      (attesa dopo arc stop)
G01 G91
X#1
M99  (return to main program)
"""


def texts(source: str) -> list[str]:
    return [line.text for line in expand_program(source).lines]


def test_variables_are_substituted_in_words():
    assert texts("#1=2.5\nG1 X#1 F100") == ["G1 X2.5 F100"]


def test_bracket_expression_is_evaluated():
    assert texts("#1=4\nG1 X[#1*2+1] F100") == ["G1 X9 F100"]


def test_negated_variable_keeps_sign_in_word():
    assert texts("#5=5\nZ-#5") == ["Z-5"]
    assert texts("#5=-5\nZ-#5") == ["Z5"]


def test_subroutine_is_repeated_with_l():
    result = expand_program("M98 P100 L3\nM30\nO100\nG1 X1 F100\nM99")
    assert [l.text for l in result.lines] == ["G1 X1 F100"] * 3
    assert all(l.line == 4 for l in result.lines)  # linha onde o comando está escrito


def test_nested_subroutines_expand_fully():
    source = "M98 P1 L2\nM30\nO1\nM98 P2 L3\nM99\nO2\nG1 X1 F100\nM99"
    assert len(texts(source)) == 6


def test_main_program_stops_at_m30():
    assert texts("G1 X1 F1\nM30\nG1 X2 F1") == ["G1 X1 F1"]


def test_undefined_subroutine_is_reported_with_line():
    issues = expand_program("M98 P9\nM30").issues
    assert issues[0].line == 1
    assert issues[0].severity == ERROR
    assert "O9" in issues[0].message


def test_recursion_is_stopped_with_error():
    issues = expand_program("M98 P1 L1\nM30\nO1\nM98 P1 L1\nM99").issues
    assert any("recursão" in issue.message for issue in issues)


def test_undefined_variable_is_reported():
    issues = expand_program("G1 X#9 F100").issues
    assert issues[0].line == 1
    assert "#9" in issues[0].message


def test_user_program_expands_to_8_layers_of_20_points():
    result = expand_program(USER_PROGRAM)
    assert result.issues == []
    assert sum(1 for l in result.lines if l.text == "X2.8") == 8 * 20
    assert result.lines[-1].text == "Z20"