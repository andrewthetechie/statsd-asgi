from logging import getLogger
from logging import Logger
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from datadog import initialize
from datadog import statsd
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from statsd_asgi._utils import get_metric_name_base

VALID_SCOPES = ["http"]


class StatusCodeMetricsMiddleware:
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
        if statsd_client is None:
            initialize(**statsd_options)
            self.statsd = statsd
        else:
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.logger.debug("starting call for scope %s", scope)
        if scope.get("type", None) not in VALID_SCOPES:
            self.logger.error(
                "Scope type %s is not yet implemented", scope.get("type", None)
            )
            await self.app(scope, receive, send)
            return

        path, method = scope["path"], scope["method"]
        try:
            metric_name_base = get_metric_name_base(self.service, path)
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while getting metric_name_base for %s on %s. Not recording metrics",
                self.service,
                path,
            )
            await self.app(scope, receive, send)
            return

        response = await self.app(scope, receive, send)
        try:
            # increment a metric for this path being requested and the status code we returned
            # For a request to mysnazzyservice.com/api/v1/endpoint this should end up like
            # mysnazzyservice.api.v1.endpoint.200
            # This metric will be tagged with the request method
            self.statsd.increment(
                f"{metric_name_base}.{response.status_code}", tags=[f"method:{method}"]
            )
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while incrementing count metric %s.%d. %s",
                metric_name_base,
                response.status_code,
                str(exc),
            )
        return
