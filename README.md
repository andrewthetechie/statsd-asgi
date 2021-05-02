# statsd-asgi
An ASGI middleware to emit metrics to statsd for requests

Mostly designed to work with Datadog, but should work with any statsd metric

## Config
statsd_client: Pass along your own statsd client. Must implement increment and timing methods
statsd_options: Options to configure the datadog statsd client
service: Name of your service, prepended to all metrics. Defaults to asgi
logger: optional logger

## Metric naming pattern
{service_name}.path
i.e.
myservice.api.v1.foo

## TimingMiddleware
Emits timing metrics for each endpoint for requests. Will emit clock time and cpu time.
### Tags
type: wall or cpu, depending on time source
status_code: The status code of the http request
method: the http method (get, post, put, delete)
## StatusCodeMetricsMiddleware 
Emits counter metrics for each endpoint
### Tags
status_code: The status code of the http request
method: the http method (get, post, put, delete)

# Usage with FastAPI
This ASGI middleware should work with any Starlette app, but I work with FastAPI so that's the example I've got for you. PRs welcome for more examples

```
from fastapi import FastAPI

app = FastAPI()

from statsd_asgi import TimingMiddleware, StatusCodeMetricsMiddleware

from logging import getLogger

statsd_options = {'statsd_host': os.environ.get("STATSD_HOST"),
                  'statsd_port': os.environ.get("STATSD_PORT")
}

app.add_middleware(TimingMiddleware, service="testapi", statsd_options=statsd_options)
app.add_middleware(StatusCodeMetricsMiddleware, service="testapi", statsd_client=statsd_options)

@app.get("/api")
async def root():
    return {"message": "Hello World"}
```
