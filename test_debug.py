import httpx
from bs4 import BeautifulSoup
import re

async def test_google_shopping():
    print("============================================================")
    print("GOOGLE SHOPPING DEBUG")
    print("============================================================")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    url = "https://www.google.com.tr/search"
    params = {
        "q": "iPhone 15",
        "tbm": "shop",
        "hl": "tr"
    }
    
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=headers)
        print(f"Status: {r.status_code}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Eğer bot korumasına düşersek sayfa başlığı farklı olur
        title = soup.title.string if soup.title else "No Title"
        print(f"Title: {title}")
        
        # Ürün kartlarını bulalım (Genellikle sh-dgr__grid-result, sh-dgr__content vb. class'lar olur)
        items = soup.select("div.sh-dgr__content, div.sh-dgr__grid-result, div[data-docid]")
        print(f"Bulunan ürün sayısı: {len(items)}")
        
        for i, item in enumerate(items[:5]):
            print(f"\n--- Ürün {i+1} ---")
            
            # Başlık
            title_el = item.select_one("h3")
            product_title = title_el.text.strip() if title_el else "Başlık Yok"
            print(f"İsim: {product_title}")
            
            # Fiyat (genellikle <span> içinde ve 'TL' içerir)
            price_text = "Fiyat Yok"
            price_els = item.find_all(string=re.compile(r'TL|₺'))
            for p in price_els:
                if any(char.isdigit() for char in p):
                    price_text = p.strip()
                    break
            print(f"Fiyat: {price_text}")
            
            # Satıcı
            seller_el = item.select_one("div.aULzUe") # Sıklıkla satıcı adını tutan class
            if not seller_el:
                # Satıcı adı genellikle fiyatın yanında veya altında bir div/span içindedir
                seller_els = item.select("div, span")
                for sel in seller_els:
                    text = sel.text.strip()
                    if len(text) > 2 and len(text) < 25 and not any(char.isdigit() for char in text) and "TL" not in text and "₺" not in text and text != product_title:
                        # Biraz basit bir tahmin yürütüyoruz
                        pass
            
            # Tüm metinleri yazdırıp satıcıyı bulmaya çalışalım
            texts = [t.strip() for t in item.strings if t.strip() and len(t.strip()) > 1]
            print(f"Tüm Metinler: {texts[:10]}") # İlk 10 metin parçasını görelim
            
        with open("debug_google_shopping.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("\n-> HTML kaydedildi: debug_google_shopping.html")

import asyncio
asyncio.run(test_google_shopping())
