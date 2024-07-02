from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple, Union, cast
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from w3lib.html import strip_html5_whitespace

if TYPE_CHECKING:
    from lxml.etree import Element  # nosec
    from lxml.html import HtmlElement  # nosec
    from lxml.html import FormElement  # nosec
    from lxml.html import InputElement  # nosec
    from lxml.html import MultipleSelectOptions  # nosec
    from lxml.html import SelectElement  # nosec
    from lxml.html import TextareaElement  # nosec

FormdataVType = Union[str, Iterable[str]]
FormdataKVType = Tuple[str, FormdataVType]
FormdataType = Optional[Union[Dict[str, FormdataVType], Iterable[FormdataKVType]]]


def _is_listlike(x: Any) -> bool:
    """Return ``True`` if *x* is a list-like object or ``False`` otherwise.

    A list-like object is an iterable, excluding strings or bytes.
    """
    return hasattr(x, "__iter__") and not isinstance(x, (str, bytes))


def _value(
    ele: InputElement | SelectElement | TextareaElement,
) -> tuple[str | None, None | str | MultipleSelectOptions]:
    n = ele.name
    v = ele.value
    if ele.tag == "select":
        return _select_value(cast("SelectElement", ele), n, v)
    return n, v


def _select_value(
    ele: SelectElement, n: str | None, v: None | str | MultipleSelectOptions
) -> tuple[str | None, None | str | MultipleSelectOptions]:
    multiple = ele.multiple
    if v is None and not multiple:
        # Match browser behavior on simple select tag without options selected
        # And for select tags without options
        o = ele.value_options
        return (n, o[0]) if o else (None, None)
    return n, v


def _url(form: FormElement, click_element: Optional[HtmlElement]) -> str:
    if form.base_url is None:
        raise ValueError(f"{form} has no base_url set.")
    action = (click_element.get("formaction") if click_element else None) or form.get("action")
    if action is None:
        return form.base_url
    return urljoin(form.base_url, strip_html5_whitespace(action))


def _method(form: FormElement, click_element: Optional[HtmlElement]) -> str:
    method = (click_element.get("formmethod") if click_element else None) or form.method
    assert method is not None  # lxml’s form.method is always filled
    method = method.upper()
    if method not in {"GET", "POST"}:
        method = "GET"
    return method


class _NoClickables(ValueError):
    pass


def _click_element(
    form: FormElement, click: None | bool | Element
) -> Optional[HtmlElement]:
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


def _data(data: FormdataType, click_element: Optional[HtmlElement]) -> FormdataType:
    data = data or {}
    if click_element and (name := click_element.get("name")):
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
        for k, v in (_value(e) for e in inputs)
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
    click: None | bool | Element = None,
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
    if form.get("enctype") == "multipart/form-data":
        raise NotImplementedError(
            f"{form} has enctype set to multipart/form-data, which "
            f"form2request does not currently support."
        )
    try:
        click_element = _click_element(form, click)
    except _NoClickables:
        raise ValueError(
            f"No clickable elements found in form {form}. Set click=False or "
            f"point it to the element to be clicked."
        )
    if click_element and click_element.get("formenctype") == "multipart/form-data":
        raise NotImplementedError(
            f"{click_element} has formenctype set to multipart/form-data, "
            f"which form2request does not currently support."
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
