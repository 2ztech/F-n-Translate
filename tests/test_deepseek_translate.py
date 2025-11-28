import requests
import json

API_KEY = "YOUR_DEEPSEEK_API_KEY"
BASE_URLS = [
    "https://api.deepseek.com",
    "https://api.deepseek.com/v1",
    # add your regional or Azure proxy URL if needed
]

def test_endpoint(base):
    url = f"{base}/translate"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "text": "Hello world",
        "source_lang": "auto",
        "target_lang": "ms"
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=5)
        print(f"Testing: {url}")
        print("Status:", r.status_code)
        print("Body:", r.text[:300], "...\n")
        return r.status_code, r.text
    except Exception as e:
        print(f"Error testing {url}: {e}\n")
        return None, None


if __name__ == "__main__":
    print("=== Testing DeepSeek Fast Translate Endpoint ===")
    for base in BASE_URLS:
        status, body = test_endpoint(base)
        if status == 200:
            print("✓ FAST TRANSLATE ENDPOINT AVAILABLE at", base)
        else:
            print("✗ No fast endpoint under", base)
