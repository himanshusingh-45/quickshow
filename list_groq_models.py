# list_groq_models.py
import os, requests, json

key = os.environ.get("GROQ_API_KEY")
base = os.environ.get("GROQ_API_URL", "https://api.groq.com").rstrip('/')
# try the OpenAI-compatible list models path:
endpoint = base
if "/openai/" not in base.lower():
    endpoint = base + "/openai/v1/models"

print("Listing models from:", endpoint)
print("GROQ_API_KEY present:", bool(key))

headers = {"Authorization": f"Bearer {key}"}
try:
    r = requests.get(endpoint, headers=headers, timeout=10)
    print("Status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print("Text:", r.text[:1000])
except Exception as e:
    print("Network error:", e)
