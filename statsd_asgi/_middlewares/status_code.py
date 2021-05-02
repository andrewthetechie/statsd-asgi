from logging import getLogger
from logging import Logger
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from datadog import initialize
from datadog import statsd
from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from statsd_asgi._utils import get_metric_name_base

VALID_SCOPES = ["http"]


class StatusCodeMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        statsd_client: Optional[Callable] = None,
        statsd_options: Optional[Dict[str, Any]] = None,
        service: str = "asgi",
        tags: Optional[List[str]] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__(app)
        self.logger = getLogger(__name__) if logger is None else logger

        if statsd_client is None:
            self.logger.debug("No statsd client, starting one")
            statsd_options = dict() if statsd_options is None else statsd_options
            initialize(**statsd_options)
            self.statsd = statsd
        else:
            self.logger.debug("Using passed in statsd_client")
            self.statsd = statsd_client

        if not hasattr(self.statsd, "increment"):
            raise NotImplementedError(
                "Your passed in statsd client does not implement a increment method to submit count stats"
            )

        if not callable(self.statsd.increment):
            raise NotImplementedError(
                "Your passed in statsd client's increment method is not callable."
            )

        self.logger = getLogger(__name__) if logger is None else logger
        self.tags = list() if tags is None else tags
        self.app = app
        self.service = service
        self.logger.debug(
            "StatusCodeMetrics middleware init complete for service %s", self.service
        )
        self.background_tasks = BackgroundTasks()

    async def dispatch(self, request: Request, call_next: Awaitable) -> None:
        self.logger.debug("starting response call for %s", request.url)

        path, method = request.url.path, request.method
        try:
            metric_name_base = get_metric_name_base(self.service, path)
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while getting metric_name_base for %s on %s. Not recording metrics",
                self.service,
                path,
            )
            return await call_next(request)

        response = await call_next(request)
        self.logger.debug(
            "Sending metric for %s response code %d",
            metric_name_base,
            response.status_code,
        )
        # increment a metric for this path being requested and the status code we returned
        # For a request to mysnazzyservice.com/api/v1/endpoint this should end up like
        # mysnazzyservice.api.v1.endpoint
        # This metric will be tagged with the request method and the status code
        try:
            self.statsd.increment(
                f"{metric_name_base}",
                tags=[f"method:{method}", f"status_code:{response.status_code}"],
            )
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while incrementing count metric %s.%d. %s",
                metric_name_base,
                response.status_code,
                str(exc),
            )

        return response
