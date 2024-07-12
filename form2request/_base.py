from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Tuple, Union
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from parsel import Selector, SelectorList
from w3lib.html import strip_html5_whitespace

if TYPE_CHECKING:
    from lxml.html import FormElement  # nosec
    from lxml.html import HtmlElement  # nosec

FormdataVType = Union[str, Iterable[str]]
FormdataKVType = Tuple[str, FormdataVType]
FormdataType = Optional[Union[Dict[str, FormdataVType], Iterable[FormdataKVType]]]


def _parsel_to_lxml(element: HtmlElement | Selector | SelectorList) -> HtmlElement:
    if isinstance(element, SelectorList):
        element = element[0]
    if isinstance(element, Selector):
        element = element.root
    return element


def _enctype(
    form: FormElement, click_element: HtmlElement | None, enctype: None | str
) -> str:
    if enctype:
        enctype = enctype.lower()
        if enctype not in {"application/x-www-form-urlencoded", "text/plain"}:
            raise ValueError(
                f"The specified form enctype ({enctype!r}) is not supported "
                f"for forms with the POST method."
            )
    elif click_element is not None and (
        enctype := (click_element.get("formenctype") or "").lower()
    ):
        if enctype == "multipart/form-data":
            raise NotImplementedError(
                f"{click_element} has formenctype set to {enctype!r}, which "
                f"form2request does not currently support for forms with the "
                f"POST method."
            )
    elif (
        enctype := (form.get("enctype") or "").lower()
    ) and enctype == "multipart/form-data":
        raise NotImplementedError(
            f"{form} has enctype set to {enctype!r}, which form2request does "
            f"not currently support for forms with the POST method."
        )
    return enctype


def _url(form: FormElement, click_element: HtmlElement | None) -> str:
    if form.base_url is None:
        raise ValueError(f"{form} has no base_url set.")
    action = (
        click_element.get("formaction") if click_element is not None else None
    ) or form.get("action")
    if action is None:
        return form.base_url
    return urljoin(form.base_url, strip_html5_whitespace(action))


USER = object()


def _method(
    form: FormElement, click_element: HtmlElement | None, method: None | str
) -> str:
    if method:
        method_src = USER
    else:
        if click_element is not None:
            method = click_element.get("formmethod")
        if method:
            method_src = click_element
        else:
            method = form.method
            assert method is not None  # lxml’s form.method is always filled
            method_src = form
    method = method.upper()
    if method_src is USER and method not in {"GET", "POST"}:
        raise ValueError(f"The specified form method ({method!r}) is not supported.")
    if method == "DIALOG":
        if method_src is click_element:
            raise NotImplementedError(
                f"Found unsupported form method {method!r} in the formmethod "
                f"attribute of the submission button."
            )
        raise NotImplementedError(f"Found unsupported form method {method!r}.")
    if method not in {"GET", "POST"}:
        method = "GET"
    return method


def _click_element(
    form: FormElement, click: None | bool | HtmlElement
) -> HtmlElement | None:
    if click is False:
        return None
    if click is None or click is True:
        clickables = list(
            form.xpath(
                'descendant::input[re:test(@type, "^(submit|image)$", "i")]'
                '|descendant::button[not(@type) or re:test(@type, "^submit$", "i")]',
                namespaces={"re": "http://exslt.org/regular-expressions"},
            )
        )
        if not clickables:
            if click:
                raise ValueError(
                    f"No clickable elements found in form {form}. Set click=False or "
                    f"point it to the element to be clicked."
                )
            else:
                return None
        click = clickables[0]
    else:
        click = _parsel_to_lxml(click)
    return click


def _data(
    form: FormElement, data: FormdataType, click_element: HtmlElement | None
) -> list[tuple[str, str]]:
    data = data or {}
    if click_element is not None and (name := click_element.get("name")):
        click_data = (name, click_element.get("value"))
        if isinstance(data, dict):
            data = dict(data)
            data[click_data[0]] = click_data[1]
        else:
            data = list(data)
            data.append(click_data)
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
    return [
        (k, v)
        for k, vs in values
        for v in ([vs] if isinstance(vs, (str, bytes)) else vs)
    ]


@dataclass
class Request:
    """HTTP request data."""

    url: str
    method: str
    headers: list[tuple[str, str]]
    body: bytes


def form2request(
    form: FormElement | Selector | SelectorList,
    data: FormdataType = None,
    *,
    click: None | bool | HtmlElement = None,
    method: None | str = None,
    enctype: None | str = None,
) -> Request:
    """Return request data for an HTML form submission.

    *form* must be an instance of :class:`parsel.selector.Selector` or
    :class:`parsel.selector.SelectorList` that points to an HTML form, or an
    instance of :class:`lxml.html.FormElement`.

    *data* should be either a dictionary of a list of 2-item tuples indicating
    the key-value pairs to include in the request as submission data. Keys with
    ``None`` as value exclude matching form fields.

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

    -   A submit button of *form*, to build a request for a form submission
        based on the clicking of that button.

        On forms with multiple submit buttons, specifying the right button here
        may be necessary.

    *method* and *enctype* may be used to override matching form attributes.
    """
    form = _parsel_to_lxml(form)
    click_element = _click_element(form, click)
    url = _url(form, click_element)
    method = _method(form, click_element, method)
    headers = []
    body = ""
    data = _data(form, data, click_element)
    if method == "GET":
        url = urlunsplit(urlsplit(url)._replace(query=urlencode(data, doseq=True)))
    else:
        assert method == "POST"
        enctype = _enctype(form, click_element, enctype)
        if enctype == "text/plain":
            headers = [("Content-Type", "text/plain")]
            body = "\n".join(f"{k}={v}" for k, v in data)
        else:
            headers = [("Content-Type", "application/x-www-form-urlencoded")]
            body = urlencode(data, doseq=True)
    return Request(
        url=url,
        method=method,
        headers=headers,
        body=body.encode(),
    )
