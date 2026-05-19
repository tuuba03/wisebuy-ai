import httpx
import asyncio
import json
from app.core.config import get_settings

settings = get_settings()

async def test_gemini_search_json():
    print("Testing Gemini with Google Search tool (JSON strict)...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": "Şu an internette 'iPhone 15 128GB siyah' araması yap. Türkiye'deki Hepsiburada, Trendyol, PttAVM, Vatan Bilgisayar gibi satıcıların anlık fiyatlarını bul. SADECE aşağıdaki JSON formatında bir çıktı ver. Başka hiçbir metin yazma:\n[\n  {\"seller_name\": \"Hepsiburada\", \"price\": 47500, \"url\": \"https://...\"}\n]"}]}],
        "tools": [{"googleSearch": {}}]
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                print("====================================")
                print(text)
            except Exception as e:
                print(f"Error parsing: {e}")
        else:
            print(f"Error: {response.text}")

asyncio.run(test_gemini_search_json())
