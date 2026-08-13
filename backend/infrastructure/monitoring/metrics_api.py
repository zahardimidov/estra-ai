from prometheus_client import Counter, Histogram

request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
request_latency = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
