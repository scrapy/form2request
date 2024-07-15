import pytest

from form2request import Request

web_poet = pytest.importorskip("web_poet")
scrapy = pytest.importorskip("scrapy")
requests = pytest.importorskip("requests")


def fake_scrapy_callback(self, response):
    pass


@pytest.mark.parametrize(
    ("request_data", "method", "kwargs", "expected"),
    (
        # GET
        *(
            (
                Request(
                    url="https://example.com?foo=bar",
                    method="GET",
                    headers=[],
                    body=b"",
                ),
                method,
                kwargs,
                expected,
            )
            for method, kwargs, expected in (
                (
                    "poet",
                    {},
                    web_poet.HttpRequest(
                        url=web_poet.RequestUrl("https://example.com?foo=bar"),
                        method="GET",
                        headers=web_poet.HttpRequestHeaders(),
                        body=web_poet.HttpRequestBody(b""),
                    ),
                ),
                (
                    "requests",
                    {},
                    requests.Request("GET", "https://example.com?foo=bar").prepare(),
                ),
                (
                    "scrapy",
                    {"callback": fake_scrapy_callback},
                    scrapy.Request(
                        "https://example.com?foo=bar", callback=fake_scrapy_callback
                    ),
                ),
            )
        ),
        # POST
        *(
            (
                Request(
                    url="https://example.com",
                    method="POST",
                    headers=[("Content-Type", "application/x-www-form-urlencoded")],
                    body=b"foo=bar",
                ),
                method,
                kwargs,
                expected,
            )
            for method, kwargs, expected in (
                (
                    "poet",
                    {},
                    web_poet.HttpRequest(
                        url=web_poet.RequestUrl("https://example.com"),
                        method="POST",
                        headers=web_poet.HttpRequestHeaders(
                            {"Content-Type": "application/x-www-form-urlencoded"}
                        ),
                        body=web_poet.HttpRequestBody(b"foo=bar"),
                    ),
                ),
                (
                    "requests",
                    {},
                    requests.Request(
                        "POST",
                        "https://example.com",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        data=b"foo=bar",
                    ).prepare(),
                ),
                (
                    "scrapy",
                    {"callback": fake_scrapy_callback},
                    scrapy.Request(
                        "https://example.com",
                        method="POST",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        body=b"foo=bar",
                        callback=fake_scrapy_callback,
                    ),
                ),
            )
        ),
        # kwargs
        (
            Request(
                url="https://example.com",
                method="POST",
                headers=[("Content-Type", "application/x-www-form-urlencoded")],
                body=b"foo=bar",
            ),
            "requests",
            {"params": {"foo": "bar"}},
            requests.Request(
                "POST",
                "https://example.com?foo=bar",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=b"foo=bar",
            ).prepare(),
        ),
        (
            Request(
                url="https://example.com",
                method="POST",
                headers=[("Content-Type", "application/x-www-form-urlencoded")],
                body=b"foo=bar",
            ),
            "scrapy",
            {"callback": fake_scrapy_callback, "meta": {"foo": "bar"}},
            scrapy.Request(
                "https://example.com",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body=b"foo=bar",
                callback=fake_scrapy_callback,
                meta={"foo": "bar"},
            ),
        ),
    ),
)
def test_conversion(request_data, method, kwargs, expected):
    actual = getattr(request_data, f"to_{method}")(**kwargs)
    if method == "poet":
        for field in ("method", "headers", "body"):
            assert getattr(actual, field) == getattr(expected, field)
        # RequestUrl(…) != RequestUrl(…)
        assert str(actual.url) == str(expected.url)
    elif method == "requests":
        # Request(…).prepare() != Request(…).prepare()
        for field in ("url", "method", "headers", "body"):
            assert getattr(actual, field) == getattr(expected, field)
    else:
        assert method == "scrapy"
        # Request(…) != Request(…)
        for field in ("url", "method", "headers", "body", "callback", "meta"):
            assert getattr(actual, field) == getattr(expected, field)
