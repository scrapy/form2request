from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple, Union, cast
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from w3lib.html import strip_html5_whitespace

if TYPE_CHECKING:
    from lxml.html import FormElement  # nosec
    from lxml.html import HtmlElement  # nosec

FormdataVType = Union[str, Iterable[str]]
FormdataKVType = Tuple[str, FormdataVType]
FormdataType = Optional[Union[Dict[str, FormdataVType], Iterable[FormdataKVType]]]


def _is_listlike(x: Any) -> bool:
    """Return ``True`` if *x* is a list-like object or ``False`` otherwise.

    A list-like object is an iterable, excluding strings or bytes.
    """
    return hasattr(x, "__iter__") and not isinstance(x, (str, bytes))


def _url(form: FormElement, click_element: HtmlElement | None) -> str:
    if form.base_url is None:
        raise ValueError(f"{form} has no base_url set.")
    action = (
        click_element.get("formaction") if click_element is not None else None
    ) or form.get("action")
    if action is None:
        return form.base_url
    return urljoin(form.base_url, strip_html5_whitespace(action))


def _method(form: FormElement, click_element: HtmlElement | None) -> str:
    method = None
    if click_element is not None:
        method = click_element.get("formmethod")
    if method:
        method_src = click_element
    else:
        method = form.method
        method_src = form
    assert method is not None  # lxml’s form.method is always filled
    upper_method = method.upper()
    if upper_method not in {"GET", "POST"}:
        attribute = "formmethod" if method_src is click_element else "method"
        raise NotImplementedError(
            f"form2request does not support the {attribute} attribute of "
            f"{method_src}: {method!r}"
        )
    return upper_method


class _NoClickables(ValueError):
    pass


def _click_element(
    form: FormElement, click: None | bool | HtmlElement
) -> HtmlElement | None:
    if click is False:
        return None
    if click in {None, True}:
        clickables = list(
            form.xpath(
                'descendant::input[re:test(@type, "^(submit|image)$", "i")]'
                '|descendant::button[not(@type) or re:test(@type, "^submit$", "i")]',
                namespaces={"re": "http://exslt.org/regular-expressions"},
            )
        )
        if not clickables:
            if click:
                raise _NoClickables
            else:
                return None
        click = clickables[0]
    return click


def _data(data: FormdataType, click_element: HtmlElement | None) -> FormdataType:
    data = data or {}
    if click_element is not None and (name := click_element.get("name")):
        click_data = (name, click_element.get("value"))
        if isinstance(data, dict):
            data = dict(data)
            data[click_data[0]] = click_data[1]
        else:
            data = list(data)
            data.append(click_data)
    return data


def _query(form: FormElement, data: FormdataType) -> str:
    keys = dict(data or ()).keys()
    if not data:
        data = []
    inputs = form.xpath(
        "descendant::textarea"
        "|descendant::select"
        "|descendant::input[not(@type) or @type["
        ' not(re:test(., "^(?:submit|image|reset)$", "i"))'
        " and (../@checked or"
        '  not(re:test(., "^(?:checkbox|radio)$", "i")))]]',
        namespaces={"re": "http://exslt.org/regular-expressions"},
    )
    values: list[FormdataKVType] = [
        (k, "" if v is None else v)
        for k, v in ((e.name, e.value) for e in inputs)
        if k and k not in keys
    ]
    items = data.items() if isinstance(data, dict) else data
    values.extend((k, v) for k, v in items if v is not None)
    encoded_values = [
        (k.encode(), v.encode())
        for k, vs in values
        for v in (cast("Iterable[str]", vs) if _is_listlike(vs) else [cast("str", vs)])
    ]
    return urlencode(encoded_values, doseq=True)


@dataclass
class Request:
    """HTTP request data."""

    url: str
    method: str
    headers: list[tuple[str, str]]
    body: bytes


def request_from_form(
    form: FormElement,
    data: FormdataType = None,
    /,
    *,
    click: None | bool | HtmlElement = None,
) -> Request:
    """Return a form submission request.

    *form* should be an instance of :class:`lxml.html.FormElement`.

    *data* should be either a dictionary of a list of 2-item tuples indicating
    the key-value pairs to include in the request as submission data.

    *click* can be any of:

    -   ``None`` (default): the first submission element of the form (e.g. a
        submit button) is used to build a request for a click-based
        form submission.

        If no submission elements are found, the request is built for a
        non-click-based form submission, i.e. a form submission triggered by a
        non-click event, such as pressing the Enter key while the focus is in
        a single-line text input field of the form.

    -   ``True`` behaves like ``None``, but raises a :exc:`ValueError`
        exception if no submission element is found in the form.

    -   ``False`` builds a request for a non-click-based form submission.

    -   A submission element of *form*, to build a request for a form submission
        based on the clicking of that specific element.

        On forms with multiple submission elements, specifying the right
        submission element here may be necessary.
    """
    try:
        click_element = _click_element(form, click)
    except _NoClickables:
        raise ValueError(
            f"No clickable elements found in form {form}. Set click=False or "
            f"point it to the element to be clicked."
        ) from None
    if click_element is not None and (enctype := click_element.get("formenctype")):
        if enctype != "application/x-www-form-urlencoded":
            raise NotImplementedError(
                f"{click_element} has formenctype set to {enctype!r}, which "
                f"form2request does not currently support."
            )
    elif (
        enctype := form.get("enctype")
    ) and enctype != "application/x-www-form-urlencoded":
        raise NotImplementedError(
            f"{form} has enctype set to {enctype!r}, which form2request does "
            f"not currently support."
        )
    url = _url(form, click_element)
    method = _method(form, click_element)
    data = _data(data, click_element)
    query = _query(form, data)
    headers = []
    body = b""
    if method == "GET":
        url = urlunsplit(urlsplit(url)._replace(query=query))
    else:
        assert method == "POST"
        headers = [("Content-Type", "application/x-www-form-urlencoded")]
        body = query.encode()
    return Request(
        url=url,
        method=method,
        headers=headers,
        body=body,
    )
