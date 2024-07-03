=====
Usage
=====

:ref:`Given an HTML form <form>`:

.. _parsel-example:

>>> from parsel import Selector
>>> html = b"""<form><input type="hidden" name="foo" value="bar" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

You can use :func:`~form2request.form2request` to generate :ref:`form
submission request data <request>`:

>>> from form2request import form2request
>>> form2request(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

:func:`~form2request.form2request` supports :ref:`user-defined form data
<data>` and :ref:`choosing a specific form submission button (or none)
<click>`.


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
    (e.g. ``#foo``) finds by ``id``, and ``[<attribute>=<value>]`` (e.g.
    ``[name=foo]``) finds by any other attribute.

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


.. _data:

Setting form data
=================

While there are forms made entirely of hidden fields, like :ref:`the one above
<fromstring-example>`, most often you will work with forms that expect
user-defined data:

>>> html = b"""<form><input type="text" name="foo" /></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

Use the second parameter of :func:`~form2request.form2request`,  to define
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

By default, if a form uses the unsupported ``dialog`` method:

>>> html = b"""<form method="dialog"></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

A :exc:`NotImplementedError` exception is raised:

>>> form2request(form)
Traceback (most recent call last):
...
NotImplementedError: Found unsupported form method 'DIALOG'.

If a form uses an unknown method:

>>> html = b"""<form method="foo"></form>"""
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")

``GET`` is used instead, as a web browser would do:

>>> form2request(form)
Request(url='https://example.com', method='GET', headers=[], body=b'')

If a website uses JavaScript to set or modify the method, use the ``method``
parameter to set the right value:

>>> form2request(form, method="GET")
Request(url='https://example.com', method='GET', headers=[], body=b'')


.. _click:

Configuring form submission
===========================

When an HTML form is submitted, the way the submission is triggered has an
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

By default, :func:`~form2request.form2request` clicks the first submission
element:

>>> form2request(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

To change that, set ``click`` to the element that should be clicked:

>>> submit_baz = form.css("[value=baz]")
>>> form2request(form, click=submit_baz)
Request(url='https://example.com?foo=baz', method='GET', headers=[], body=b'')


.. _request:

Using request data
==================

:class:`~form2request.Request` is a simple data container that you can use to
build an actual request object:

>>> request_data = form2request(form)

Here are some examples for popular Python libraries and frameworks:

>>> from requests import Request
>>> request = Request(request_data.method, request_data.url, headers=request_data.headers, data=request_data.body)
>>> request
<Request [GET]>


>>> from scrapy import Request
>>> request = Request(request_data.url, method=request_data.method, headers=request_data.headers, body=request_data.body)
>>> request
<GET https://example.com?foo=bar>
