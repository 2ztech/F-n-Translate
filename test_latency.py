import requests
import time
start = time.perf_counter()
requests.get("https://api.deepseek.com/ping").raise_for_status()
print(f"API latency: {(time.perf_counter()-start)*1000:.0f}ms")  # Should be <300ms
