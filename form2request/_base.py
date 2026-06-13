from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from parsel import Selector, SelectorList
from w3lib.html import strip_html5_whitespace

if TYPE_CHECKING:
    import requests
    import scrapy
    import web_poet
    from lxml.html import FormElement, HtmlElement


@dataclass
class FileField:
    """A file upload value for use with multipart/form-data forms."""

    content: bytes
    filename: str = ""
    content_type: str = "application/octet-stream"


FormdataVType: TypeAlias = str | FileField | Iterable[str]
FormdataKVType: TypeAlias = tuple[str, FormdataVType]
FormdataType: TypeAlias = dict[str, FormdataVType] | Iterable[FormdataKVType] | None


def _parsel_to_lxml(
    element: HtmlElement | Selector | SelectorList,
) -> HtmlElement:
    if isinstance(element, SelectorList):
        return element[0].root
    if isinstance(element, Selector):
        return element.root
    return element


def _enctype(
    form: FormElement, click_element: HtmlElement | None, enctype: None | str
) -> str:
    if enctype:
        enctype = enctype.lower()
        if enctype not in {
            "application/x-www-form-urlencoded",
            "text/plain",
            "multipart/form-data",
        }:
            raise ValueError(
                f"The specified form enctype ({enctype!r}) is not supported "
                f"for forms with the POST method."
            )
    elif (
        click_element is not None
        and (enctype := (click_element.get("formenctype") or "").lower())
    ) or (enctype := (form.get("enctype") or "").lower()):
        pass
    return enctype or ""


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
            assert method is not None  # lxml's form.method is always filled
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
    form: FormElement, click: bool | HtmlElement | Selector | SelectorList | None
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
        if clickables:
            return clickables[0]
        if click:
            raise ValueError(
                f"No clickable elements found in form {form}. Set click=False or "
                f"point it to the element to be clicked."
            )
        return None
    return _parsel_to_lxml(click)


def _data(
    form: FormElement, data: FormdataType, click_element: HtmlElement | None
) -> list[tuple[str, str | FileField]]:
    data = data or {}
    if click_element is not None and (name := click_element.get("name")):
        click_data = (name, cast("str", click_element.get("value")))
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
        for k, v in (
            (
                # Unset name for selects without options.
                (None, None)
                if e.tag == "select" and not e.value_options
                else (e.name, e.value)
            )
            for e in inputs
        )
        if k and k not in keys
    ]
    items = data.items() if isinstance(data, dict) else data
    values.extend((k, v) for k, v in items if v is not None)
    return [
        (k, v)
        for k, vs in values
        for v in ([vs] if isinstance(vs, (str, bytes, FileField)) else vs)
    ]


def _build_multipart_body(
    data: list[tuple[str, str | FileField]], boundary: str
) -> bytes:
    parts = []
    for name, value in data:
        if isinstance(value, FileField):
            filename_part = f'; filename="{value.filename}"' if value.filename else ""
            header = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"{filename_part}\r\n'
                f"Content-Type: {value.content_type}\r\n"
                f"\r\n"
            ).encode()
            parts.append(header + value.content + b"\r\n")
        else:
            header = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            ).encode()
            parts.append(header + value.encode() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


@dataclass
class Request:
    """HTTP request data."""

    url: str
    method: str
    headers: list[tuple[str, str]]
    body: bytes

    def to_poet(self, **kwargs: Any) -> web_poet.HttpRequest:
        """Convert the request to :class:`web_poet.HttpRequest
        <web_poet.page_inputs.http.HttpRequest>`.

        All *kwargs* are passed to :class:`web_poet.HttpRequest
        <web_poet.page_inputs.http.HttpRequest>` as is.
        """
        import web_poet  # noqa: PLC0415

        return web_poet.HttpRequest(
            url=self.url,
            method=self.method,
            headers=self.headers,
            body=self.body,
            **kwargs,
        )

    def to_requests(self, **kwargs: Any) -> requests.PreparedRequest:
        """Convert the request to :class:`requests.PreparedRequest`.

        All *kwargs* are passed to :class:`requests.Request` as is.
        """
        import requests  # noqa: PLC0415

        request = requests.Request(
            self.method,
            self.url,
            headers=dict(self.headers),
            data=self.body,
            **kwargs,
        )
        return request.prepare()

    def to_scrapy(self, callback: Callable, **kwargs: Any) -> scrapy.Request:
        """Convert the request to :class:`scrapy.Request`.

        All *kwargs* are passed to :class:`scrapy.Request` as is.
        """
        import scrapy  # noqa: PLC0415

        return scrapy.Request(
            self.url,
            callback=callback,
            method=self.method,
            headers=self.headers,
            body=self.body,
            **kwargs,
        )


def form2request(
    form: FormElement | Selector | SelectorList,
    data: FormdataType = None,
    *,
    click: bool | HtmlElement | Selector | SelectorList | None = None,
    method: None | str = None,
    enctype: None | str = None,
) -> Request:
    """Return request data for an HTML form submission.

    *form* must be an instance of :class:`parsel.selector.Selector` or
    :class:`parsel.selector.SelectorList` that points to an HTML form, or an
    instance of :class:`lxml.html.FormElement`.

    *data* should be either a dictionary or a list of 2-item tuples indicating
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
    form_el = cast("FormElement", _parsel_to_lxml(form))
    click_element = _click_element(form_el, click)
    url = _url(form_el, click_element)
    method = _method(form_el, click_element, method)
    data = _data(form_el, data, click_element)
    if method == "GET":
        url = urlunsplit(urlsplit(url)._replace(query=urlencode(data, doseq=True)))
        return Request(url=url, method=method, headers=[], body=b"")
    assert method == "POST"
    enctype = _enctype(form_el, click_element, enctype)
    if enctype == "multipart/form-data":
        boundary = uuid.uuid4().hex
        headers = [("Content-Type", f'multipart/form-data; boundary="{boundary}"')]
        return Request(
            url=url,
            method=method,
            headers=headers,
            body=_build_multipart_body(data, boundary),
        )
    if enctype == "text/plain":
        body = "\n".join(f"{k}={v}" for k, v in data)
        return Request(
            url=url,
            method=method,
            headers=[("Content-Type", "text/plain")],
            body=body.encode(),
        )
    body = urlencode(data, doseq=True)
    return Request(
        url=url,
        method=method,
        headers=[("Content-Type", "application/x-www-form-urlencoded")],
        body=body.encode(),
    )
