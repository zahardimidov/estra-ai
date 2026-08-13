from prometheus_client import Counter, Gauge, Histogram

ml_inference_time = Histogram(
    "ml_inference_duration_seconds",
    "ML inference latency",
    ["input_type"],
)
queue_size = Gauge(
    "moderation_queue_size",
    "Current length of the Redis moderation queue",
)
processed_tasks_total = Counter(
    "processed_tasks_total",
    "Total moderation tasks processed",
)
blocked_tasks_total = Counter(
    "blocked_tasks_total",
    "Total moderation tasks resulting in a blocked decision",
)
