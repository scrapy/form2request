=====
Usage
=====

:ref:`Given an HTML form <form>`:

.. _parsel-example:

>>> from parsel import Selector
>>> html = b"""<form><input type="hidden" name="foo" value="bar" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

You can use :func:`~form2request.form2request` to generate form submission
request data:

>>> from form2request import form2request
>>> request_data = form2request(form)
>>> request_data
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

:func:`~form2request.form2request` does not make requests, but you can use its
output to build requests with any HTTP client software. It also provides
:ref:`conversion methods for common use cases <request>`, e.g. for the
:doc:`requests <requests:index>` library:

.. _requests-example:

>>> import requests
>>> request = request_data.to_requests()
>>> requests.send(request)  # doctest: +SKIP
<Response [200]>

:func:`~form2request.form2request` supports :ref:`user-defined form data
<data>`, :ref:`choosing a specific submit button (or none) <click>`, and
:ref:`overriding form attributes <override>`.


.. _form:

Getting a form
==============

:func:`~form2request.form2request` requires an HTML form object. You can get
one using :doc:`parsel <parsel:index>`, as :ref:`seen above <parsel-example>`,
or you can use :doc:`lxml <lxml:index>`:

.. _fromstring-example:

>>> from lxml.html import fromstring
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

If you use a library or framework based on :doc:`parsel <parsel:index>` or
:doc:`lxml <lxml:index>`, chances are they also let you get a form object. For
example, when using a :doc:`Scrapy <scrapy:index>` response:

>>> from scrapy.http import TextResponse
>>> response = TextResponse("https://example.com", body=html)
>>> form = response.css("form")

Here are some examples of XPath expressions that can be useful to get a form
using parsel’s :meth:`Selector.xpath <parsel.selector.Selector.xpath>` or
lxml’s :meth:`HtmlElement.xpath <lxml.html.HtmlElement.xpath>`:

-   To find a form by one of its attributes, such as ``id`` or ``name``, use
    ``//form[@<attribute>="<value>"]``. For example, to find ``<form id="foo"
    …``, use ``//form[@id="foo"]``.

    When using :meth:`Selector.css <parsel.selector.Selector.css>`, ``#<id>``
    (e.g. ``#foo``) finds by ``id``, and ``[<attribute>="<value>"]`` (e.g.
    ``[name=foo]`` or ``[name="foo bar"]``) finds by any other attribute.

-   To find a form by index, by order of appearance in the HTML code, use
    ``(//form)[n]``, where ``n`` is a 1-based index. For example, to find the
    2nd form, use ``(//form)[2]``.

If you prefer, you could use the XPath of an element inside the form, and then
visit parent elements until you reach the form element. For example:

.. code-block:: python

    element = root.xpath('//input[@name="zip_code"]')[0]
    while True:
        if element.tag == "form":
            break
        element = element.getparent()
    form = element

For some use cases, you can use :doc:`Formasaurus <formasaurus:index>`, a
ML-based solution that can can automatically find a form of a specified type
(e.g. a search form), its :ref:`default key-value pairs <data>`, and its
:ref:`submit button <click>`. It’s :ref:`formasaurus:usage` documentation
includes an example featuring form2request.


.. _data:

Setting form data
=================

While there are forms made entirely of hidden fields, like :ref:`the one above
<fromstring-example>`, most often you will work with forms that expect
user-defined data:

>>> html = b"""<form><input type="text" name="foo" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

Use the ``data`` parameter of :func:`~form2request.form2request`,  to define
the corresponding data:

>>> form2request(form, {"foo": "bar"})
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

You may sometimes find forms where more than one field has the same ``name``
attribute:

>>> html = b"""<form><input type="text" name="foo" /><input type="text" name="foo" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

To specify values for all same-name fields, instead of a dictionary, use an
iterable of key-value tuples:

>>> form2request(form, (("foo", "bar"), ("foo", "baz")))
Request(url='https://example.com?foo=bar&foo=baz', method='GET', headers=[], body=b'')

.. _remove-data:

Sometimes, you might want to prevent a value from a field from being included
in the generated request data. For example, because the field is removed or
disabled through JavaScript, or because the field or a parent element has the
``disabled`` attribute (currently not supported by form2request):

>>> html = b"""<form><input name="foo" value="bar" disabled /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

To remove a field value, set it to ``None``:

>>> form2request(form, {"foo": None})
Request(url='https://example.com', method='GET', headers=[], body=b'')


.. _click:

Choosing a submit button
========================

When an HTML form is submitted, the way form submission is triggered has an
impact on the resulting request data.

Given a submit button with ``name`` and ``value`` attributes:

>>> html = b"""<form><input type="submit" name="foo" value="bar" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

If you submit the form by clicking that button, those attributes are included
in the request data, which is what :func:`~form2request.form2request` does
by default:

>>> form2request(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

However, sometimes it is possible to submit a form without clicking a submit
button, even when there is such a button. In such cases, the button data should
not be part of the request data. For such cases, set ``click`` to ``False``:

>>> form2request(form, click=False)
Request(url='https://example.com', method='GET', headers=[], body=b'')

You may also find forms with more than one submit button:

>>> html = b"""<form><input type="submit" name="foo" value="bar" /><input type="submit" name="foo" value="baz" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

By default, :func:`~form2request.form2request` clicks the first submit button:

>>> form2request(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

To change that, set ``click`` to the element that should be clicked:

>>> submit_baz = form.css("[value=baz]")
>>> form2request(form, click=submit_baz)
Request(url='https://example.com?foo=baz', method='GET', headers=[], body=b'')


.. _override:

Overriding form attributes
==========================

You can override the method_ and enctype_ attributes of a form:

.. _enctype: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/form#enctype
.. _method: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/form#method

>>> form2request(form, method="POST", enctype="text/plain")
Request(url='https://example.com', method='POST', headers=[('Content-Type', 'text/plain')], body=b'foo=bar')


.. _request:

Using request data
==================

The output of :func:`~form2request.form2request`,
:class:`~form2request.Request`, is a simple request data container:

>>> request_data = form2request(form)
>>> request_data
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

While :func:`~form2request.form2request` does not make requests, you can use
its output request data to build an actual request with any HTTP client
software.

:class:`~form2request.Request` also provides conversion methods for common use
cases:

-   :meth:`~form2request.Request.to_scrapy`, for :doc:`Scrapy 1.1.0+
    <scrapy:index>`:

    >>> request_data.to_scrapy(callback=self.parse)  # doctest: +SKIP
    <GET https://example.com?foo=bar>

-   :meth:`~form2request.Request.to_requests`, for :doc:`requests 1.0.0+
    <requests:index>` (see an example :ref:`above <requests-example>`).

-   :meth:`~form2request.Request.to_poet`, for :doc:`web-poet 0.2.0+
    <poet:index>`:

    >>> request_data.to_poet()
    HttpRequest(url=RequestUrl('https://example.com?foo=bar'), method='GET', headers=<HttpRequestHeaders()>, body=b'')
