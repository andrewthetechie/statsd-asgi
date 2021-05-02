import resource
import time
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


class TimingMiddleware:
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

        if not hasattr(self.statsd, "timing"):
            raise NotImplementedError(
                "Your passed in statsd client does not implement a timing method to submit timing stats"
            )

        if not callable(self.statsd.timing):
            raise NotImplementedError(
                "Your passed in statsd client's timing method is not callable."
            )

        self.logger = getLogger(__name__) if logger is None else logger
        self.tags = list() if tags is None else tags
        self.app = app
        self.service = service
        self.logger.debug(
            "Timing middleware init complete for service %s", self.service
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.logger.debug("starting timing call for scope %s", scope)
        start_time = time.time()
        cpu_start_time = self._get_cpu_time()
        if scope.get("type", None) not in VALID_SCOPES:
            self.logger.error(
                "Scope type %s is not yet implemented for timing",
                scope.get("type", None),
            )
            await self.app(scope, receive, send)
            return

        path, method = scope["path"], scope["method"]
        try:
            metric_name_base = get_metric_name_base(self.service, path)
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while getting metric_name_base for %s on %s. Not recording timing metrics",
                self.service,
                path,
            )
            await self.app(scope, receive, send)
            return

        response = await self.app(scope, receive, send)
        stop_time = time.time()
        cpu_stop_time = self._get_cpu_time()
        try:
            self.statsd.timing(
                f"{metric_name_base}",
                stop_time - start_time,
                tags=[
                    f"method:{method}",
                    f"status_code:{response.status_code}",
                    "type:clock",
                ],
            )
            self.statsd.timing(
                f"{metric_name_base}",
                cpu_stop_time - cpu_start_time,
                tags=[
                    f"method:{method}",
                    f"status_code:{response.status_code}",
                    "type:cpu",
                ],
            )
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while submitting timing metric %s. %s",
                metric_name_base,
                str(exc),
            )
        return

    @staticmethod
    def _get_cpu_time():
        """Returns a combo of usertime + system time"""
        cpu_time = resource.getrusage(resource.RUSAGE_SELF)
        return cpu_time[0] + cpu_time[1]
