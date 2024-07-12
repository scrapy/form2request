import pytest
from lxml.html import fromstring
from parsel import Selector

from form2request import Request, form2request


@pytest.mark.parametrize(
    ("base_url", "html", "kwargs", "expected"),
    (
        # Empty form.
        (
            "https://example.com",
            b"""<form></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Hidden field.
        (
            "https://example.com",
            b"""<form><input type="hidden" name="a" value="b" /></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # User data not defined by any form field.
        # We need to support this, for example, to make it easy to deal with
        # forms that may have fields injected with JavaScript.
        (
            "https://example.com",
            b"""<form></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # User data setting a value for a form field.
        (
            "https://example.com",
            b"""<form><input type="text" name="a" /></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # User data overriding the value of a form field.
        # Also needed for JavaScript use cases.
        (
            "https://example.com",
            b"""<form><input type="hidden" name="a" value="b" /></form>""",
            {"data": {"a": "c"}},
            Request(
                "https://example.com?a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # User data with None as value not present in the form is ignored.
        (
            "https://example.com",
            b"""<form></form>""",
            {"data": {"a": None}},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # User data setting a value from a form field to None removes that
        # value.
        (
            "https://example.com",
            b"""<form><input type="text" name="a" /></form>""",
            {"data": {"a": None}},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # User data overriding the value of a form field to None removes that
        # value.
        (
            "https://example.com",
            b"""<form><input type="hidden" name="a" value="b" /></form>""",
            {"data": {"a": None}},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Form field with an unset value.
        (
            "https://example.com",
            b"""<form><input type="text" name="a" /></form>""",
            {},
            Request(
                "https://example.com?a=",
                "GET",
                [],
                b"",
            ),
        ),
        # User data as an iterable of key-value tuples.
        (
            "https://example.com",
            b"""<form></form>""",
            {"data": (("a", "b"), ("a", "c"))},
            Request(
                "https://example.com?a=b&a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # A submit button is “clicked” by default, i.e. its attributes are
        # taken into account.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" /></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # You can disable the clicking of any submit button.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" /></form>""",
            {"click": False},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # You can force the clicking of the first submit button.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" /></form>""",
            {"click": True},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # Forcing the clicking of the first submit button will trigger a
        # ValueError if there are no submit buttons.
        (
            "https://example.com",
            b"""<form></form>""",
            {"click": True},
            ValueError,
        ),
        # If there are 2 or more submit buttons, the first one is used by
        # default.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" />
            <input type="submit" name="a" value="c" /></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # You can force a specific submit button to be used.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" />
            <input type="submit" name="a" value="c" /></form>""",
            {"click": './/*[@value="c"]'},
            Request(
                "https://example.com?a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Supported enctypes are application/x-www-form-urlencoded (default)
        # and text/plain. Unknown enctypes are treated as the default one.
        *(
            (
                "https://example.com",
                f"""<form enctype="{enctype}"></form>""".encode(),
                {},
                Request(
                    "https://example.com",
                    "GET",
                    [],
                    b"",
                ),
            )
            for enctype in (
                "",
                "application/x-www-form-urlencoded",
                "text/plain",
                "foo",
            )
        ),
        # multipart/form-data raises a NotImplementedError exception when the
        # method is POST.
        (
            "https://example.com",
            b"""<form enctype="multipart/form-data" method="post"></form>""",
            {},
            NotImplementedError,
        ),
        # multipart/form-data does work when method is GET (default).
        (
            "https://example.com",
            b"""<form enctype="multipart/form-data">
            <input name="a" value="b" /></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # The formenctype from the submit button is taken into account, even if
        # it has an unknown value.
        (
            "https://example.com",
            b"""<form enctype="multipart/form-data" method="post"><input type="submit"
            formenctype="application/x-www-form-urlencoded" /></form>""",
            {},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form enctype="multipart/form-data" method="post"><input type="submit"
            formenctype="foo" /></form>""",
            {},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form enctype="application/x-www-form-urlencoded" method="post">
            <input type="submit" formenctype="multipart/form-data" /></form>""",
            {},
            NotImplementedError,
        ),
        # enctype may be overridden, in which case it raises ValueError for
        # both unknown and unsupported values when method is POST.
        (
            "https://example.com",
            b"""<form method="post"></form>""",
            {"enctype": "multipart/form-data"},
            ValueError,
        ),
        (
            "https://example.com",
            b"""<form method="post"></form>""",
            {"enctype": "a"},
            ValueError,
        ),
        # Only submit buttons are detected as such.
        *(
            (
                "https://example.com",
                f"""<form>{button}<button name="c" value="d" /></form>""".encode(),
                {},
                Request(
                    "https://example.com?a=b",
                    "GET",
                    [],
                    b"",
                ),
            )
            for button in (
                """<input type="image" name="a" value="b" />""",
                """<input type="submit" name="a" value="b" />""",
                """<button name="a" value="b" />""",
                """<button type="submit" name="a" value="b" />""",
            )
        ),
        # Other buttons are not “clicked”.
        *(
            (
                "https://example.com",
                f"""<form>{button}<button name="c" value="d" /></form>""".encode(),
                {},
                Request(
                    f"https://example.com?{query}",
                    "GET",
                    [],
                    b"",
                ),
            )
            for button, query in (
                # Not treated as a button, but as an input its name and value
                # still make it into the request data.
                (
                    """<input type="button" name="a" value="b" />""",
                    "a=b&c=d",
                ),
                (
                    """<button type="" name="a" value="b" />""",
                    "c=d",
                ),
            )
        ),
        # The action of the form is taken into account.
        (
            "https://example.com",
            b"""<form action="a"></form>""",
            {},
            Request(
                "https://example.com/a",
                "GET",
                [],
                b"",
            ),
        ),
        # The formaction of the submit button takes precedence.
        (
            "https://example.com",
            b"""<form action="a"><button type="submit" formaction="b" /></form>""",
            {},
            Request(
                "https://example.com/b",
                "GET",
                [],
                b"",
            ),
        ),
        # Spaces in the action attribute are stripped.
        (
            "https://example.com",
            b"""<form action=" a "></form>""",
            {},
            Request(
                "https://example.com/a",
                "GET",
                [],
                b"",
            ),
        ),
        # The method of the form is taken into account.
        (
            "https://example.com",
            b"""<form method="get"></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form method="post"></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"a=b",
            ),
        ),
        # The formmethod of the submit button overrides the form method.
        (
            "https://example.com",
            b"""<form method="post"><button type="submit" formmethod="get" /></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form method="get"><button formmethod="post" /></form>""",
            {"data": {"a": "b"}},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"a=b",
            ),
        ),
        # The dialog method triggers a NotImplementedError, but only if it is
        # the actual method to be used, e.g. not if overridden by another
        # method.
        (
            "https://example.com",
            b"""<form method="dialog"></form>""",
            {},
            NotImplementedError,
        ),
        (
            "https://example.com",
            b"""<form><button formmethod="dialog" /></form>""",
            {},
            NotImplementedError,
        ),
        (
            "https://example.com",
            b"""<form method="dialog"><button formmethod="get" /></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form method="dialog"><button formmethod="a" /></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Unknown methods are replaced with GET.
        (
            "https://example.com",
            b"""<form method="a"></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form><button formmethod="a" /></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # If an unknown method is defined in a submit button and the parent
        # form has a valid method, the submit button method (GET) still takes
        # precedence.
        (
            "https://example.com",
            b"""<form method="post"><button formmethod="a" /></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Users can override the method value, to work around scenarios where
        # HTML forms have an unsupported method but a supported one is set
        # through JavaScript.
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="b" /></form>""",
            {"method": "get"},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # If users pass dialog as method, ValueError is raised instead of
        # NotImplementedError, since users should know that it is not a
        # supported value beforehand.
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="b" /></form>""",
            {"method": "dialog"},
            ValueError,
        ),
        # If users pass an unknown method, ValueError is raised since users
        # should know which values are supported beforehand.
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="b" /></form>""",
            {"method": "c"},
            ValueError,
        ),
        # User data as an iterable of key-value tuples gets merged with button
        # name and value as expected.
        (
            "https://example.com",
            b"""<form><button name="d" value="e"></form>""",
            {"data": (("a", "b"), ("a", "c"))},
            Request(
                "https://example.com?a=b&a=c&d=e",
                "GET",
                [],
                b"",
            ),
        ),
        # We currently do not support ignoring disabled form elements.
        pytest.param(
            "https://example.com",
            b"""<form><input disabled name="a" value="b"></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
            marks=pytest.mark.xfail(reason="No disabled support"),
        ),
        pytest.param(
            "https://example.com",
            b"""<form><fieldset disabled><input name="a" value="b">
            </fieldset></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
            marks=pytest.mark.xfail(reason="No disabled support"),
        ),
        # Single-choice select with a single option.
        (
            "https://example.com",
            b"""<form><select name="a"><option value="b">B</option></select></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # Single-choice select with a single option with no value.
        (
            "https://example.com",
            b"""<form><select name="a"><option>B</option></select></form>""",
            {},
            Request(
                "https://example.com?a=B",
                "GET",
                [],
                b"",
            ),
        ),
        # Single-choice select with no options.
        (
            "https://example.com",
            b"""<form><select name="a"></select></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Single-choice select with no options but with a value.
        (
            "https://example.com",
            b"""<form><select name="a" value="b"></select></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Single-choice select with multiple options. The first one is
        # selected.
        (
            "https://example.com",
            b"""<form><select name="a"><option value="b">B</option>
            <option value="c">C</option></select></form>""",
            {},
            Request(
                "https://example.com?a=b",
                "GET",
                [],
                b"",
            ),
        ),
        # Single-choice select with multiple options, one of which is selected.
        (
            "https://example.com",
            b"""<form><select name="a"><option value="b">B</option>
            <option selected value="c">C</option></select></form>""",
            {},
            Request(
                "https://example.com?a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Multiple-choice select with multiple options, none of which is
        # selected.
        (
            "https://example.com",
            b"""<form><select multiple name="a"><option value="b">B</option>
            <option value="c">C</option></select></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Multiple-choice select with multiple options, one of which is
        # selected.
        (
            "https://example.com",
            b"""<form><select multiple name="a"><option value="b">B</option>
            <option value="c" selected>C</option></select></form>""",
            {},
            Request(
                "https://example.com?a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Multiple-choice select with multiple options, all of which are
        # selected.
        (
            "https://example.com",
            b"""<form><select multiple name="a"><option value="b" selected>B</option>
            <option value="c" selected>C</option></select></form>""",
            {},
            Request(
                "https://example.com?a=b&a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Multiple-choice select without options.
        (
            "https://example.com",
            b"""<form><select multiple name="a"></select></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Multiple-choice select without options but with a value.
        (
            "https://example.com",
            b"""<form><select multiple name="a" value="b"></select></form>""",
            {},
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Values are URL-encoded, with plus signs instead of spaces.
        (
            "https://example.com",
            b"""<form><input name="a+ /" value="b+ /"></form>""",
            {"data": {"c+ /": "d+ /"}},
            Request(
                "https://example.com?a%2B+%2F=b%2B+%2F&c%2B+%2F=d%2B+%2F",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form method="post"><input name="a+ /" value="b+ /"></form>""",
            {"data": {"c+ /": "d+ /"}},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"a%2B+%2F=b%2B+%2F&c%2B+%2F=d%2B+%2F",
            ),
        ),
        # When using the text/plain enctype, things work the same for GET, but
        # for POST values are not URL-encoded, and line breaks are used as
        # separators.
        (
            "https://example.com",
            b"""<form enctype="text/plain"><input name="a+ /" value="b+ /"></form>""",
            {"data": {"c+ /": "d+ /"}},
            Request(
                "https://example.com?a%2B+%2F=b%2B+%2F&c%2B+%2F=d%2B+%2F",
                "GET",
                [],
                b"",
            ),
        ),
        (
            "https://example.com",
            b"""<form enctype="text/plain" method="post">
            <input name="a+ /" value="b+ /"></form>""",
            {"data": {"c+ /": "d+ /"}},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "text/plain")],
                b"a+ /=b+ /\nc+ /=d+ /",
            ),
        ),
        # enctype and formenctype are treated case-insensitively.
        (
            "https://example.com",
            b"""<form enctype="TeXt/PlAiN" method="post">
            <input name="a+ /" value="b+ /"></form>""",
            {"data": {"c+ /": "d+ /"}},
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "text/plain")],
                b"a+ /=b+ /\nc+ /=d+ /",
            ),
        ),
        (
            "https://example.com",
            b"""<form enctype="application/x-www-form-urlencoded" method="post">
            <input type="submit" formenctype="MuLtIpArT/fOrM-dAtA" /></form>""",
            {},
            NotImplementedError,
        ),
    ),
)
def test_form2request(base_url, html, kwargs, expected):
    root = fromstring(html, base_url=base_url)
    form = root.xpath("//form")[0]
    click = kwargs.pop("click", None)
    if isinstance(click, str):
        click = form.xpath(click)[0]
    if isinstance(expected, Request):
        actual = form2request(form, click=click, **kwargs)
        assert expected == actual
    else:
        with pytest.raises(expected):
            form2request(form, click=click, **kwargs)


def test_form2request_no_base_url():
    html = "<form></form>"
    root = fromstring(html)
    form = root.xpath("//form")[0]
    with pytest.raises(ValueError):
        form2request(form)


def test_form2request_parsel():
    html = b"""<form><input type="submit" name="foo" value="bar" />
    <input type="submit" name="foo" value="baz" /></form>"""
    selector = Selector(body=html, base_url="https://example.com")
    form = selector.css("form")

    expected = Request(
        url="https://example.com?foo=bar", method="GET", headers=[], body=b""
    )
    assert form2request(form) == expected
    assert form2request(form[0]) == expected
    assert form2request(form[0].root) == expected

    submit_baz = form.css("[value=baz]")
    expected = Request(
        url="https://example.com?foo=baz", method="GET", headers=[], body=b""
    )
    assert form2request(form, click=submit_baz) == expected
    assert form2request(form, click=submit_baz[0]) == expected
    assert form2request(form, click=submit_baz[0].root) == expected
