import pytest
from lxml.html import fromstring

from form2request import Request, request_from_form


@pytest.mark.parametrize(
    ("base_url", "html", "data", "click", "method", "expected"),
    (
        # Empty form.
        (
            "https://example.com",
            b"""<form></form>""",
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            {"a": "b"},
            None,
            None,
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
            {"a": "b"},
            None,
            None,
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
            {"a": "c"},
            None,
            None,
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
            {"a": None},
            None,
            None,
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
            {"a": None},
            None,
            None,
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
            {"a": None},
            None,
            None,
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
            None,
            None,
            None,
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
            (("a", "b"), ("a", "c")),
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            False,
            None,
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
            None,
            True,
            None,
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
            None,
            True,
            None,
            ValueError,
        ),
        # If there are 2 or more submit buttons, the first one is used by
        # default.
        (
            "https://example.com",
            b"""<form><input type="submit" name="a" value="b" />
            <input type="submit" name="a" value="c" /></form>""",
            None,
            None,
            None,
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
            None,
            './/*[@value="c"]',
            None,
            Request(
                "https://example.com?a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Only the application/x-www-form-urlencoded enctype (default) is
        # supported.
        *(
            (
                "https://example.com",
                f"""<form enctype="{enctype}"></form>""".encode(),
                None,
                None,
                None,
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
            )
        ),
        # Any other raise a NotImplementedError expection.
        *(
            (
                "https://example.com",
                f"""<form enctype="{enctype}"></form>""".encode(),
                None,
                None,
                None,
                NotImplementedError,
            )
            for enctype in (
                "multipart/form-data",
                "text/plain",
                "foo",
            )
        ),
        # The formenctype from the submit button is taken into account.
        (
            "https://example.com",
            b"""<form enctype="foo"><input type="submit"
            formenctype="application/x-www-form-urlencoded" /></form>""",
            None,
            None,
            None,
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Even if the form has an unsupported enctype, things work if the
        # submit button sets a supported one.
        (
            "https://example.com",
            b"""<form enctype="application/x-www-form-urlencoded"><input
            type="submit" formenctype="foo" /></form>""",
            None,
            None,
            None,
            NotImplementedError,
        ),
        # Only submit buttons are detected as such.
        *(
            (
                "https://example.com",
                f"""<form>{button}<button name="c" value="d" /></form>""".encode(),
                None,
                None,
                None,
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
                None,
                None,
                None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            {"a": "b"},
            None,
            None,
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
            {"a": "b"},
            None,
            None,
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
            {"a": "b"},
            None,
            None,
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
            {"a": "b"},
            None,
            None,
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"a=b",
            ),
        ),
        # Unsupported methods trigger a NotImplementedError, but only if they
        # are the actual method to be used, e.g. not if overridden by a
        # supported method.
        (
            "https://example.com",
            b"""<form method="a"></form>""",
            None,
            None,
            None,
            NotImplementedError,
        ),
        (
            "https://example.com",
            b"""<form><button formmethod="a" /></form>""",
            None,
            None,
            None,
            NotImplementedError,
        ),
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="get" /></form>""",
            None,
            None,
            None,
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # Users can override the method value, to workaround scenarios where
        # HTML forms have an unsupported method but a supported one is set
        # through JavaScript.
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="b" /></form>""",
            None,
            None,
            "get",
            Request(
                "https://example.com",
                "GET",
                [],
                b"",
            ),
        ),
        # If users pass an unsupported method, ValueError is raised instead of
        # NotImplementedError, since users should know which values are
        # supported beforehand.
        (
            "https://example.com",
            b"""<form method="a"><button formmethod="b" /></form>""",
            None,
            None,
            "c",
            ValueError,
        ),
        # User data as an iterable of key-value tuples gets merged with button
        # name and value as expected.
        (
            "https://example.com",
            b"""<form><button name="d" value="e"></form>""",
            (("a", "b"), ("a", "c")),
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
            Request(
                "https://example.com?a=B",
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
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
            None,
            None,
            None,
            Request(
                "https://example.com?a=b&a=c",
                "GET",
                [],
                b"",
            ),
        ),
        # Values are URL-encoded, with plus signs instead of spaces.
        (
            "https://example.com",
            b"""<form><input name="a+ /" value="b+ /"></form>""",
            {"c+ /": "d+ /"},
            None,
            None,
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
            {"c+ /": "d+ /"},
            None,
            None,
            Request(
                "https://example.com",
                "POST",
                [("Content-Type", "application/x-www-form-urlencoded")],
                b"a%2B+%2F=b%2B+%2F&c%2B+%2F=d%2B+%2F",
            ),
        ),
    ),
)
def test_request_from_form(base_url, html, data, click, method, expected):
    root = fromstring(html, base_url=base_url)
    form = root.xpath("//form")[0]
    if isinstance(click, str):
        click = form.xpath(click)[0]
    if isinstance(expected, Request):
        actual = request_from_form(form, data, click=click, method=method)
        assert expected == actual
    else:
        with pytest.raises(expected):
            request_from_form(form, data, click=click, method=method)


def test_request_from_form_no_base_url():
    html = "<form></form>"
    root = fromstring(html)
    form = root.xpath("//form")[0]
    with pytest.raises(ValueError):
        request_from_form(form)
