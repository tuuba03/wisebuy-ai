import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_sikayetvar_search():
    seller_name = "getmobil"
    url = f"https://html.duckduckgo.com/html/"
    params = {"q": f"site:sikayetvar.com {seller_name}"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=params, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = soup.select(".result__snippet")
        print(f"Results for {seller_name}:")
        for res in results[:3]:
            print("-", res.text.strip())

asyncio.run(test_sikayetvar_search())
