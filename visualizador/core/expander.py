"""Expansão de sub-rotinas (O, M98, M99), repetições (L) e variáveis (#n).

Produz a sequência de linhas na ordem em que a máquina as executaria. Não depende
de Qt nem de numpy.
"""
from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass, field

from config import MAX_CALL_DEPTH, MAX_EXPANDED_LINES
from core.lexer import ERROR, WARNING, GCodeError, Issue, clean_line, parse_words

SUB_LABEL_RE = re.compile(r"^O(\d+)$")
ASSIGN_RE = re.compile(r"^#(\d+)\s*=\s*(.+)$")
VARIABLE_RE = re.compile(r"#(\d+)")
SIGNED_VARIABLE_RE = re.compile(r"(-?)#(\d+)")
BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")

END_CODES = {2, 30}             # M2 e M30: fim do programa
CONTROL_CODES = {2, 30, 98, 99}  # M2, M30, M98 (chama sub-rotina), M99 (retorna)
RETURN_CODE = 99
CALL_CODE = 98

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


@dataclass(frozen=True)
class SourceLine:
    """Uma linha executada. 'line' é onde o comando está escrito no arquivo."""
    line: int
    text: str


@dataclass
class Subroutine:
    line: int
    body: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class Expansion:
    lines: list[SourceLine] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def expand_program(text: str) -> Expansion:
    """Transforma o texto do programa na sequência de linhas executadas."""
    return ProgramExpander(text).run()


def safe_eval(expr: str) -> float:
    """Avalia uma expressão aritmética simples (+ - * / e parênteses). Sem nomes nem chamadas."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as err:
        raise GCodeError(f"expressão inválida: {expr!r}") from err
    return _eval_node(tree.body, expr)


def _eval_node(node: ast.AST, expr: str) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, expr))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left = _eval_node(node.left, expr)
        right = _eval_node(node.right, expr)
        if isinstance(node.op, ast.Div) and right == 0:
            raise GCodeError(f"divisão por zero em {expr!r}")
        return _BINARY_OPS[type(node.op)](left, right)
    raise GCodeError(f"expressão não suportada: {expr!r}")


def _format(value: float) -> str:
    """Número em notação decimal simples, para caber nas palavras do G-code."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _m_codes(text: str) -> set[int]:
    return {int(value) for letter, value in parse_words(text) if letter == "M"}


def _is_standalone(text: str) -> bool:
    """Linha de controle deve conter apenas M, P e L."""
    return all(letter in "MPL" for letter, _ in parse_words(text))


def _word(words: list[tuple[str, float]], letter: str, default: float | None = None):
    for name, value in words:
        if name == letter:
            return value
    return default


class ProgramExpander:
    def __init__(self, text: str) -> None:
        self._variables: dict[int, float] = {}
        self._subs: dict[int, Subroutine] = {}
        self._main: list[tuple[int, str]] = []
        self._out: list[SourceLine] = []
        self._issues: list[Issue] = []
        self._stopped = False
        self._split(text)

    def run(self) -> Expansion:
        self._execute(self._main, depth=0)
        return Expansion(self._out, self._issues)

    # --- primeira passada: separa programa principal e sub-rotinas ---

    def _split(self, text: str) -> None:
        """Sub-rotinas podem ficar depois do M30, então todas são coletadas antes de executar."""
        current: Subroutine | None = None
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = clean_line(raw)
            if not line:
                continue

            label = SUB_LABEL_RE.match(line)
            if label:
                number = int(label.group(1))
                if number in self._subs:
                    self._report(lineno, WARNING,
                                 f"sub-rotina O{number} definida mais de uma vez")
                current = Subroutine(line=lineno)
                self._subs[number] = current
                continue

            if current is None:
                self._main.append((lineno, line))
            else:
                current.body.append((lineno, line))
                if RETURN_CODE in _m_codes(line):
                    current = None

    # --- segunda passada: executa na ordem da máquina ---

    def _execute(self, lines: list[tuple[int, str]], depth: int) -> None:
        for lineno, text in lines:
            if self._stopped:
                return

            assignment = ASSIGN_RE.match(text)
            if assignment:
                self._assign(lineno, assignment)
                continue

            try:
                text = self._substitute(text)
            except GCodeError as err:
                self._report(lineno, ERROR, str(err))
                continue

            codes = _m_codes(text)
            if codes & CONTROL_CODES:
                if not _is_standalone(text):
                    self._report(lineno, ERROR,
                                 "M98, M99 e M30 devem estar sozinhos na linha; linha ignorada")
                    continue
                if codes & END_CODES:
                    self._stopped = True
                    return
                if RETURN_CODE in codes:
                    return
                if CALL_CODE in codes:
                    self._call(lineno, text, depth)
                continue

            self._emit(lineno, text)

    def _call(self, lineno: int, text: str, depth: int) -> None:
        words = parse_words(text)
        target = _word(words, "P")
        repeat = _word(words, "L", 1.0)

        if target is None:
            self._report(lineno, ERROR, "M98 sem P (número da sub-rotina)")
            return
        if repeat < 1 or repeat != int(repeat):
            self._report(lineno, ERROR, f"L inválido no M98: {repeat:g}")
            return

        number = int(target)
        sub = self._subs.get(number)
        if sub is None:
            self._report(lineno, ERROR, f"sub-rotina O{number} não encontrada")
            return
        if depth >= MAX_CALL_DEPTH:
            self._report(lineno, ERROR,
                         f"chamadas aninhadas acima de {MAX_CALL_DEPTH} níveis; possível recursão")
            return

        for _ in range(int(repeat)):
            if self._stopped:
                return
            self._execute(sub.body, depth + 1)

    def _emit(self, lineno: int, text: str) -> None:
        if len(self._out) >= MAX_EXPANDED_LINES:
            self._report(lineno, ERROR,
                         f"programa expandido acima de {MAX_EXPANDED_LINES} linhas; "
                         "expansão interrompida")
            self._stopped = True
            return
        self._out.append(SourceLine(lineno, text))

    # --- variáveis ---

    def _assign(self, lineno: int, match: re.Match) -> None:
        number = int(match.group(1))
        try:
            self._variables[number] = self._evaluate(match.group(2))
        except GCodeError as err:
            self._report(lineno, ERROR, str(err))

    def _lookup(self, number: int) -> float:
        if number not in self._variables:
            raise GCodeError(f"variável #{number} não definida")
        return self._variables[number]

    def _evaluate(self, expr: str) -> float:
        expr = VARIABLE_RE.sub(lambda m: f"({_format(self._lookup(int(m.group(1))))})", expr)
        return safe_eval(expr)

    def _substitute(self, text: str) -> str:
        """Resolve [expressões] e depois #n, mantendo o sinal de -#n."""
        text = BRACKET_RE.sub(lambda m: _format(self._evaluate(m.group(1))), text)
        return SIGNED_VARIABLE_RE.sub(self._replace_variable, text)

    def _replace_variable(self, match: re.Match) -> str:
        value = self._lookup(int(match.group(2)))
        if match.group(1):  # -#n: nega o valor da variável
            value = -value
        return _format(value)

    # --- relatório ---

    def _report(self, lineno: int, severity: str, message: str) -> None:
        self._issues.append(Issue(lineno, severity, message))