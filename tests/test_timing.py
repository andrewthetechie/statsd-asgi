import pytest
from asgi_tools.app import App
from asgi_tools.tests import ASGITestClient
from starlette.responses import HTMLResponse
from starlette.testclient import TestClient


def test_timing_invalid_statsd():
    from statsd_asgi import TimingMiddleware

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        response = HTMLResponse("<html><body>Hello, world!</body></html>")
        await response(scope, receive, send)

    class FakeStatsd:
        ...

    with pytest.raises(NotImplementedError) as error:
        app = TimingMiddleware(app, statsd_client=FakeStatsd())

    assert error.type == NotImplementedError

    class FakeStatsd2:
        @property
        def timing(self):
            return

    with pytest.raises(NotImplementedError) as error:
        app = TimingMiddleware(app, statsd_client=FakeStatsd2())

    assert error.type == NotImplementedError


def test_timing_statsd_options(mocker):
    import statsd_asgi
    from statsd_asgi import TimingMiddleware

    mocker.patch.object(statsd_asgi.middlewares.timing, "initialize", return_value="")
    mocker.patch.object(statsd_asgi.middlewares.timing, "statsd", return_value="")

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        response = HTMLResponse("<html><body>Hello, world!</body></html>")
        await response(scope, receive, send)

    app = TimingMiddleware(
        app, statsd_options={"statsd_host": "testhost", "statsd_port": 1234}
    )
    statsd_asgi.middlewares.timing.initialize.assert_called_once_with(
        **{"statsd_host": "testhost", "statsd_port": 1234}
    )


def test_timing_dispatch(mocker):
    import statsd_asgi
    from statsd_asgi import TimingMiddleware

    mocker.patch.object(statsd_asgi.middlewares.timing, "initialize", return_value="")
    mocker.patch.object(
        statsd_asgi.middlewares.timing, "statsd", return_value="", create=True
    )

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        response = HTMLResponse("<html><body>Hello, world!</body></html>")
        await response(scope, receive, send)

    app = TimingMiddleware(
        app, statsd_options={"statsd_host": "testhost", "statsd_port": 1234}
    )
    client = TestClient(app)
    response = client.get("/api")
    assert response.status_code == 200
    statsd_asgi.middlewares.timing.statsd.timing.assert_called()
    # TODO: test the calls of this mock, being lazy for now


def test_timing_dispatch_bad_name(mocker):
    import statsd_asgi
    from statsd_asgi import TimingMiddleware

    mocker.patch.object(statsd_asgi.middlewares.timing, "initialize", return_value="")
    mocker.patch.object(
        statsd_asgi.middlewares.timing, "statsd", return_value="", create=True
    )
    mocker.patch.object(
        statsd_asgi.middlewares.timing,
        "get_metric_name_base",
        return_value="",
        side_effect=Exception("error"),
    )

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        response = HTMLResponse("<html><body>Hello, world!</body></html>")
        await response(scope, receive, send)

    app = TimingMiddleware(
        app, statsd_options={"statsd_host": "testhost", "statsd_port": 1234}
    )
    client = TestClient(app)
    response = client.get("/api")
    assert response.status_code == 200
    statsd_asgi.middlewares.timing.statsd.timing.assert_not_called()
    # TODO: This test could be way better
