"""One synchronous worker: bounded memory and process-local rate limits by default."""

import os

bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
control_socket_disable = True
worker_class = "sync"
threads = 1
timeout = 30
graceful_timeout = 30
keepalive = 2
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190
errorlog = "-"
# Do not retain URLs, IP addresses or upload data in application access logs.
accesslog = None
loglevel = "warning"
forwarded_allow_ips = ""  # Proxy trust is explicit in the application configuration.

if workers > 1 and os.environ.get("DBCRAFTER_RATELIMIT_STORAGE_URI", "memory://") == "memory://":
    raise RuntimeError("Configure shared rate-limit storage before enabling multiple workers")
