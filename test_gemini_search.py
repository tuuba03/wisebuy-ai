import httpx
import asyncio
import json
from app.core.config import get_settings

settings = get_settings()

async def test_gemini_search():
    print("Testing Gemini with Google Search tool...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": "Bana iPhone 15 128GB için Türkiye'deki en güncel 5 satıcıyı ve fiyatlarını liste halinde ver. (Akakçe, Hepsiburada, Trendyol vb. kaynaklardan)"}]}],
        "tools": [{"googleSearch": {}}]
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                print("====================================")
                print("GEMINI RESPONSE WITH SEARCH:")
                print("====================================")
                print(text)
                
                # Search grounding metadata if any
                if "groundingMetadata" in data["candidates"][0]:
                    print("\n[Has Grounding Metadata]")
            except Exception as e:
                print(f"Error parsing: {e}")
                print(data)
        else:
            print(f"Error: {response.text}")

asyncio.run(test_gemini_search())
