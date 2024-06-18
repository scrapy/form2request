project = "form2request"
copyright = "Zyte Group Ltd"
release = "0.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

html_theme = "sphinx_rtd_theme"

autodoc_member_order = "groupwise"

intersphinx_disabled_reftypes = []
intersphinx_mapping = {
    "lxml": ("https://lxml.de/apidoc/", None),
    "parsel": ("https://parsel.readthedocs.io/en/stable", None),
    "python": ("https://docs.python.org/3", None),
}
