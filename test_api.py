import httpx

API_KEY = "AIzaSyCHoOtpi2DXvjC8NNkMotCANRP8Dcs1FG4"

# 1. Hangi modeller kullanılabilir?
print("=== KULLANILABILIR MODELLER ===")
r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}")
if r.status_code == 200:
    for m in r.json().get("models", []):
        name = m["name"]
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            print(f"  ✅ {name}")
else:
    print(f"  HATA: {r.status_code} - {r.text[:200]}")

print()

# 2. v1 ile de deneyelim
print("=== v1 API ile MODELLER ===")
r2 = httpx.get(f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}")
if r2.status_code == 200:
    for m in r2.json().get("models", []):
        name = m["name"]
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            print(f"  ✅ {name}")
else:
    print(f"  HATA: {r2.status_code} - {r2.text[:200]}")

print()

# 3. Basit bir istek deneyelim
print("=== TEST: gemini-2.0-flash (v1beta) ===")
r3 = httpx.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}",
    json={"contents": [{"parts": [{"text": "Merhaba, 2+2 kaçtır?"}]}]},
    timeout=30
)
print(f"  Status: {r3.status_code}")
if r3.status_code == 200:
    print(f"  Cevap: {r3.json()['candidates'][0]['content']['parts'][0]['text']}")
else:
    print(f"  Hata: {r3.text[:300]}")
