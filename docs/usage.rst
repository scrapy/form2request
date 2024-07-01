=====
Usage
=====

:ref:`Given an HTML form <form>`:

.. _fromstring-example:

>>> from lxml.html import fromstring
>>> html = b"""<form><input type="hidden" name="foo" value="bar" /></form>"""
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

You can use :func:`~form2request.request_from_form` to generate :ref:`form
submission request data <request>`:

>>> from form2request import request_from_form
>>> request_from_form(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

:func:`~form2request.request_from_form` supports :ref:`user-defined form data
<data>` and :ref:`choosing a specific form submission button (or none)
<click>`.


.. _form:

Getting a form
==============

:func:`~form2request.request_from_form` requires an
:class:`lxml.html.FormElement` object.

You can build one using :func:`lxml.html.fromstring` to parse an HTML document
and :meth:`lxml.html.HtmlElement.xpath` to find a form element in that
document, as :ref:`seen above <fromstring-example>`.

Here are some examples of XPath expressions that can be useful to find a form
element using :meth:`~lxml.html.HtmlElement.xpath`:

-   To find a form by one of its attributes, such as ``id`` or ``name``, use
    ``//form[@<attribute>="<value>"]``. For example, to find ``<form id="foo"
    …``, use ``//form[@id="foo"]``.

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

If you use an lxml-based library or framework, chances are they also let you
get a :class:`~lxml.html.FormElement` object. For example, when using
:doc:`parsel <parsel:index>`:

>>> from parsel import Selector
>>> selector = Selector(body=html, base_url="https://example.com")
>>> form = selector.css("form")[0].root
>>> type(form)
<class 'lxml.html.FormElement'>

A similar example, with a :doc:`Scrapy <scrapy:index>` response:

>>> from scrapy.http import TextResponse
>>> response = TextResponse("https://example.com", body=html)
>>> form = response.css("form")[0].root
>>> type(form)
<class 'lxml.html.FormElement'>


.. _data:

Setting form data
=================

While there are forms made entirely of hidden fields, like :ref:`the one above
<fromstring-example>`, most often you will work with forms that expect
user-defined data:

>>> html = b"""<form><input type="text" name="foo" /></form>"""
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

Use the second parameter of :func:`~form2request.request_from_form`,  to define
the corresponding data:

>>> request_from_form(form, {"foo": "bar"})
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

You may sometimes find forms where more than one field has the same ``name``
attribute:

>>> html = b"""<form><input type="text" name="foo" /><input type="text" name="foo" /></form>"""
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

To specify values for all same-name fields, instead of a dictionary, use an
iterable of key-value tuples:

>>> request_from_form(form, (("foo", "bar"), ("foo", "baz")))
Request(url='https://example.com?foo=bar&foo=baz', method='GET', headers=[], body=b'')


.. _click:

Configuring form submission
===========================

When an HTML form is submitted, the way the submission is triggered has an
impact on the resulting request data.

Given a submit button with ``name`` and ``value`` attributes:

>>> html = b"""<form><input type="submit" name="foo" value="bar" /></form>"""
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

If you submit the form by clicking that button, those attributes are included
in the request data, which is what :func:`~form2request.request_from_form` does
by default:

>>> request_from_form(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

However, sometimes it is possible to submit a form without clicking a submit
button, even when there is such a button. In such cases, the button data should
not be part of the request data. For such cases, set ``click`` to ``False``:

>>> request_from_form(form, click=False)
Request(url='https://example.com', method='GET', headers=[], body=b'')

You may also find forms with more than one submit button:

>>> html = b"""<form><input type="submit" name="foo" value="bar" /><input type="submit" name="foo" value="baz" /></form>"""
>>> root = fromstring(html, base_url="https://example.com")
>>> form = root.xpath("//form")[0]

By default, :func:`~form2request.request_from_form` clicks the first submission
element:

>>> request_from_form(form)
Request(url='https://example.com?foo=bar', method='GET', headers=[], body=b'')

To change that, set ``click`` to the element that should be clicked:

>>> submit_baz = form.xpath('.//*[@value="baz"]')[0]
>>> request_from_form(form, click=submit_baz)
Request(url='https://example.com?foo=baz', method='GET', headers=[], body=b'')


.. _request:

Using request data
==================

:class:`~form2request.Request` is a simple data container that you can use to
build an actual request object:

>>> request_data = request_from_form(form)

Here are some examples for popular Python libraries and frameworks:

>>> from requests import Request
>>> request = Request(request_data.method, request_data.url, headers=request_data.headers, data=request_data.body)
>>> request
<Request [GET]>


>>> from scrapy import Request
>>> request = Request(request_data.url, method=request_data.method, headers=request_data.headers, body=request_data.body)
>>> request
<GET https://example.com?foo=bar>
