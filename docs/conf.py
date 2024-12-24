project = "form2request"
copyright = "Zyte Group Ltd"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

html_theme = "sphinx_rtd_theme"

intersphinx_disabled_reftypes = []
intersphinx_mapping = {
    "formasaurus": ("https://formasaurus.readthedocs.io/en/latest/", None),
    "lxml": ("https://lxml.de/apidoc/", None),
    "parsel": ("https://parsel.readthedocs.io/en/stable", None),
    "poet": ("https://web-poet.readthedocs.io/en/latest/", None),
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "scrapy": ("https://docs.scrapy.org/en/latest", None),
}

nitpick_ignore = [
    *(
        ("py:class", cls)
        for cls in (
            # https://github.com/sphinx-doc/sphinx/issues/11225
            "FormdataType",
            "FormElement",
            "HtmlElement",
            "Selector",
            "SelectorList",
        )
    ),
]
