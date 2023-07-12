from doctest import ELLIPSIS

from sybil import Sybil
from sybil.parsers.rest import DocTestParser, PythonCodeBlockParser


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS),
        PythonCodeBlockParser(),
    ],
    patterns=["*.md", "*.py"],
).pytest()
