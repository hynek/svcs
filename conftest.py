from doctest import ELLIPSIS

from sybil import Sybil
from sybil.parsers.myst import (
    DocTestDirectiveParser as MarkdownDocTestParser,
    PythonCodeBlockParser as MarkdownPythonCodeBlockParser
)
from sybil.parsers.rest import (
    DocTestParser as ReSTDocTestParser,
    PythonCodeBlockParser as ReSTPythonCodeBlockParser
)

markdown_examples = Sybil(
    parsers=[
        MarkdownDocTestParser(optionflags=ELLIPSIS),
        MarkdownPythonCodeBlockParser(),
    ],
    patterns=['*.md'],
    fixtures=['keep_seed']
)

rest_examples = Sybil(
    parsers=[
        ReSTDocTestParser(optionflags=ELLIPSIS),
        ReSTPythonCodeBlockParser(),
    ],
    patterns=['*.py'],
    fixtures=['keep_seed']
)

pytest_collect_file = (markdown_examples+rest_examples).pytest()
