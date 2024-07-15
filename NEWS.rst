=============
Release notes
=============

0.2.0 (2024-07-DD)
==================

:class:`~form2request.Request` now provides conversion methods for :doc:`Scrapy
<scrapy:index>` (:meth:`~form2request.Request.to_scrapy`), :doc:`requests
<requests:index>` (:meth:`~form2request.Request.to_requests`), and
:doc:`web-poet <poet:index>` (:meth:`~form2request.Request.to_poet`).

0.1.1 (2024-07-12)
==================

The name of a ``select`` element is now ignored if that ``select`` element has
no nested ``option`` elements, in line with browser behavior.


0.1.0 (2024-07-12)
==================

Initial release.
