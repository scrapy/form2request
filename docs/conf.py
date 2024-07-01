project = "form2request"
copyright = "Zyte Group Ltd"
release = "0.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

html_theme = "sphinx_rtd_theme"

intersphinx_disabled_reftypes = [
    "lxml.etree.FormElement",
]
intersphinx_mapping = {
    "lxml": ("https://lxml.de/apidoc/", None),
    "parsel": ("https://parsel.readthedocs.io/en/stable", None),
    "python": ("https://docs.python.org/3", None),
    "scrapy": ("https://docs.scrapy.org/en/latest", None),
}

nitpick_ignore = [
    *(
        ("py:class", cls)
        for cls in (
            # https://github.com/sphinx-doc/sphinx/issues/11225
            "Element",
            "FormdataType",
            "FormElement",
        )
    ),
]
