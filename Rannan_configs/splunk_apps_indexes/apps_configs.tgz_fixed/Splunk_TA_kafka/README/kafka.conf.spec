[global_settings]
log_level = log level of this AddOn
index = default Splunk index
use_kv_store = 0 or 1. 1 means use KV Store to do checkpoint
use_multiprocess_consumer = 0 or 1. 1 means use multiprocess to do data collection, otherwise use multithreading
fetch_message_max_bytes = Maximum bytes for each topic/partition fetch request.  Defaults to 1024*1024.


# Don't need to configure proxy_settings for Kafka TA
[proxy_settings]
proxy_enabled = 0 or 1. 1 means enable proxy
proxy_url =
proxy_port =
proxy_username =
proxy_password =

# If use proxy to do DNS resolution, set proxy_rdns to 1
proxy_rdns = 0

# Valid proxy_type are http, http_no_tunnel, socks4, socks5
proxy_type = http
