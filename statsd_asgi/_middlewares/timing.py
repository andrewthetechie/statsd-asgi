import resource
import time
from logging import getLogger
from logging import Logger
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional

from datadog import initialize
from datadog import statsd
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from statsd_asgi._utils import get_metric_name_base


class TimingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        statsd_client: Optional[Callable] = None,
        statsd_options: Optional[Dict[str, Any]] = None,
        service: str = "asgi",
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__(app)
        if statsd_client is None:
            statsd_options = dict() if statsd_options is None else statsd_options
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
        self.app = app
        self.service = service
        self.logger.debug(
            "Timing middleware init complete for service %s", self.service
        )

    async def dispatch(self, request: Request, call_next: Awaitable) -> None:
        self.logger.debug("starting timing call for request %s", request.url)
        start_time = time.time()
        cpu_start_time = self._get_cpu_time()
        self.logger.debug("Start time clock %d cpu %d", start_time, cpu_start_time)

        path, method = request.url.path, request.method
        try:
            metric_name_base = get_metric_name_base(self.service, path)
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.error(
                "Error while getting metric_name_base for %s on %s. Not recording timing metrics",
                self.service,
                path,
            )
            return await call_next(request)

        response = await call_next(request)
        stop_time = time.time()
        cpu_stop_time = self._get_cpu_time()
        self.logger.debug("Stop time clock %d cpu %d", stop_time, cpu_stop_time)
        self.logger.debug(
            "Total time clock %f cpu %f",
            stop_time - start_time,
            cpu_stop_time - cpu_start_time,
        )
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
        return response

    @staticmethod
    def _get_cpu_time():
        """Returns a combo of usertime + system time"""
        cpu_time = resource.getrusage(resource.RUSAGE_SELF)
        return cpu_time[0] + cpu_time[1]
