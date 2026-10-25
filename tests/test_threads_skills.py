import pytest

from hn_glut.skills import match, plain_text
from hn_glut.threads import classify


@pytest.mark.parametrize("title,expected", [
    ("Ask HN: Who is hiring? (October 2026)", ("hiring", "2026-10")),
    ("Ask HN: Who Is Hiring? (March 2015) ", ("hiring", "2015-03")),
    (" Ask HN: Freelancer? Seeking freelancer? (June 2019)", ("freelancer", "2019-06")),
    ("Ask HN: Freelancer? Seeking Freelancers? (May 2016)", ("freelancer", "2016-05")),
    ("Ask HN: Who wants to be hired? (July 2014)", ("seeking", "2014-07")),
    ("Ask HN: Who is hiring? (January, 2016)", ("hiring", "2016-01")),
    ("Ask HN: Who is hiring right now?", None),
    ("Ask HN: Who is meeting up? (December 2012)", None),
    ("Ask HN: Who is hiring? (Smarch 2020)", None),
])
def test_classify(title, expected):
    assert classify(title) == expected


def test_plain_text_strips_html():
    assert plain_text("Acme&#x2F;Co<p>We use <i>C++</i> &amp; Go") == "acme/co\nwe use  c++  & go"


@pytest.mark.parametrize("text,yes,no", [
    ("Technologies: Python, Go, Rust", {"python", "go", "rust"}, set()),
    ("Stack: Python/Go", {"go"}, set()),
    ("Golang microservices", {"go"}, set()),
    ("I want to go to Berlin and go big", set(), {"go"}),
    ("JavaScript and TypeScript", {"javascript", "typescript"}, {"java"}),
    ("Java, Kotlin", {"java", "kotlin"}, {"javascript"}),
    ("C++ and C#", {"c++", "c#/.net"}, set()),
    ("Node.js, React.js", {"node", "react"}, set()),
    ("We build agentic systems with LLMs", {"ai agents", "llm"}, set()),
    ("ML / PyTorch", {"ml"}, set()),
    ("HTML and XML", set(), {"ml"}),
    ("front-end and frontend", {"frontend"}, set()),
])
def test_skill_match(text, yes, no):
    found = match(text)
    assert yes <= found
    assert not (no & found)
