from urllib.parse import urlparse


def get_metric_name_base(service_name: str, path: str) -> str:
    """Turns a service name and a path being accessed into a
    metric name for statsd (dot separated).

    i.e. For a request to mysnazzyservice.com/api/v1/endpoint
    this should return mysnazzyservice.api.v1.endpoint.200
    """
    return f"{service_name}{urlparse(path).path.replace('/', '.')}"
