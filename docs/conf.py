# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from importlib import metadata


# We want an image in the README and include the README in the docs.
suppress_warnings = ["image.nonlocal_uri"]


# -- General configuration ----------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",  # MUST be up here!
    "notfound.extension",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxext.opengraph",
]

myst_enable_extensions = [
    "colon_fence",
    "smartquotes",
    "deflist",
]

ogp_image = "https://svcs.hynek.me/en/latest/_static/social%20card.png"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "svcs"
author = "Hynek Schlawack"
copyright = f"2023, { author }"


# The full version, including alpha/beta/rc tags.
release = metadata.version("svcs")
# The short X.Y version.
version = release.rsplit(".", 1)[0]

if "dev" in release:
    release = version = "UNRELEASED"

exclude_patterns = ["_build"]

nitpick_ignore = [
    ("py:class", "AbstractAsyncContextManager"),
    ("py:class", "aiohttp.web_request.Request"),
    ("py:class", "FastAPI"),
]

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).

# Move type hints into the description block, instead of the func definition.
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"
# None of the options work, so we disable the button completely.
html_theme_options = {
    "top_of_page_button": None,
    "sidebar_hide_name": True,
}
html_logo = "_static/logo_with_name.svg"
html_static_path = ["_static"]

htmlhelp_basename = "svcsdoc"

_descr = f"{metadata.metadata('svcs')['summary']} for Python."
_title = "svcs"
rst_epilog = f"""\
.. meta::
    :property=og:type: website
    :property=og:site_name: { _title }
    :property=og:description: { _descr }
    :property=og:author: Hynek Schlawack
    :twitter:title: { _title }
    :twitter:creator: @hynek
"""

# GitHub has rate limits
linkcheck_ignore = [
    r"https://github.com/.*/(issues|pull|compare)/\d+",
    r"https://twitter.com/.*",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "aiohttp": ("https://docs.aiohttp.org/en/stable/", None),
    "flask": ("https://flask.palletsprojects.com/en/latest/", None),
    "pyramid": (
        "https://docs.pylonsproject.org/projects/pyramid/en/main/",
        None,
    ),
}
