"""Deterministic skill matching on comment text. One regex per skill; a comment counts once per skill."""

from __future__ import annotations

import html
import re

# Applied to lower-cased plain text. Keep each pattern covered by tests/test_skills.py.
SKILLS: dict[str, str] = {
    "python": r"\bpython\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "typescript": r"\btypescript\b",
    "react": r"\breact(?:\.?js)?\b",
    "node": r"\bnode\.?js\b",
    # "go" alone is an English verb; only count it in list context ("Go, Rust" / "Python/Go" / "(Go)").
    "go": r"\bgolang\b|(?:^|[,/(|:]\s*)go\b(?=\s*(?:[,/)|.;]|$|\n))",
    "rust": r"\brust\b",
    "java": r"\bjava\b",
    "kotlin": r"\bkotlin\b",
    "swift": r"\bswift\b",
    "c++": r"c\+\+|\bcpp\b",
    "c#/.net": r"c#|\.net\b|\bdotnet\b",
    "ruby": r"\bruby\b|\brails\b",
    "php": r"\bphp\b",
    "elixir": r"\belixir\b",
    "scala": r"\bscala\b",
    "sql": r"\bsql\b|\bpostgres(?:ql)?\b|\bmysql\b",
    "aws": r"\baws\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "ml": r"machine learning|\bml\b|\bpytorch\b|\btensorflow\b",
    "llm": r"\bllms?\b|\bgenai\b|\bgpt\b|\brag\b",
    "ai agents": r"\bagents?\b|\bagentic\b",
    "data engineering": r"\bdata engineer(?:ing)?\b|\bspark\b|\bairflow\b|\bdbt\b",
    "devops/sre": r"\bdevops\b|\bsre\b|site reliability|\bterraform\b",
    "frontend": r"\bfront[- ]?end\b",
    "ios": r"\bios\b",
    "android": r"\bandroid\b",
    "security": r"\bsecurity\b|\bappsec\b|\bpentest",
    "embedded": r"\bembedded\b|\bfirmware\b",
}
_COMPILED = {name: re.compile(p, re.M) for name, p in SKILLS.items()}

_TAG = re.compile(r"<[^>]+>")
_BREAK = re.compile(r"<(?:p|br)\s*/?>", re.I)


def plain_text(comment_html: str) -> str:
    """HN comment HTML -> lower-cased plain text, paragraphs on separate lines."""
    text = _BREAK.sub("\n", comment_html)
    text = _TAG.sub(" ", text)
    return html.unescape(text).lower()


def match(comment_html: str) -> set[str]:
    text = plain_text(comment_html)
    return {name for name, rx in _COMPILED.items() if rx.search(text)}
