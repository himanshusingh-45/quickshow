import os, json, requests

key = os.environ.get("GROQ_API_KEY")
base = os.environ.get("GROQ_API_URL", "https://api.groq.com").rstrip('/')
model = os.environ.get("GROQ_MODEL", "gpt-4o-mini")  # change to correct provider model

if "/openai/" in base.lower():
    endpoint = base
else:
    endpoint = base + "/openai/v1/chat/completions"

print("Using endpoint:", endpoint)
print("Using model:", model)
print("GROQ_API_KEY present:", bool(key))

payload = {
    "model": model,
    "messages": [
        {"role":"system", "content":"You are QuickShow assistant."},
        {"role":"user", "content":"hello"}
    ],
    "max_tokens": 50
}
headers = {"Authorization": f"Bearer {key}", "Content-Type":"application/json"}

r = requests.post(endpoint, json=payload, headers=headers, timeout=10)
print("Status:", r.status_code)
try:
    print("JSON:", json.dumps(r.json(), indent=2))
except:
    print("Text:", r.text[:500])
