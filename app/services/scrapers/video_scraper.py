import httpx
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from loguru import logger
import re
import json
import urllib.parse

from app.core.config import get_settings
from app.core.exceptions import VideoTranscriptException

settings = get_settings()

YOUTUBE_SEARCH_URL = "https://www.youtube.com/results"

class VideoScraperService:
    def __init__(self):
        self.headers = {"User-Agent": settings.scraper_user_agent}
        self.timeout = settings.scraper_timeout

    async def get_youtube_summaries(self, product_name: str) -> list[dict]:
        logger.info(f"[YouTube] Searching for: {product_name}")
        video_ids = await self._search_youtube_video_ids(product_name)
        results = []

        for video_id in video_ids[: settings.youtube_max_videos]:
            try:
                transcript = await self._fetch_transcript(video_id)
                results.append(
                    {
                        "platform": "youtube",
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "transcript": transcript,
                    }
                )
            except VideoTranscriptException as e:
                logger.warning(str(e))
                continue

        logger.success(f"[YouTube] Got transcripts for {len(results)} videos")
        return results

    async def _search_youtube_video_ids(self, query: str) -> list[str]:
        """YouTube'da en popüler inceleme videolarını arar."""
        # Hem Türkçe hem İngilizce inceleme terimlerini dene
        search_query = f"{query} inceleme review kullanıcı yorumu"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                YOUTUBE_SEARCH_URL,
                params={"search_query": search_query, "sp": "CAM%253D"},  # Görüntülenme sayısına göre sırala
                headers=self.headers,
            )
            response.raise_for_status()

        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text)
        seen = set()
        unique_ids = []
        for vid in video_ids:
            if vid not in seen:
                seen.add(vid)
                unique_ids.append(vid)

        return unique_ids[:10]

    async def _fetch_transcript(self, video_id: str) -> str:
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.fetch(video_id, languages=["tr", "en"])
            full_text = " ".join(entry.text for entry in transcript_list)
            return full_text[:10000]  # Daha uzun transcript = daha zengin analiz
        except Exception as e:
            raise VideoTranscriptException(video_id, str(e))

    async def get_tiktok_summaries(self, product_name: str) -> list[dict]:
        """DuckDuckGo üzerinden TikTok içeriklerini bulur."""
        logger.info(f"[TikTok] Searching for: {product_name}")
        results = []

        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            params = {"q": f"site:tiktok.com {product_name} inceleme"}

            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(ddg_url, data=params, headers=self.headers)

                if response.status_code != 200:
                    logger.warning(f"[TikTok] DuckDuckGo returned {response.status_code}")
                    return results

                soup = BeautifulSoup(response.text, "html.parser")

                seen_urls = set()
                count = 0
                
                for result in soup.select("div.result"):
                    if count >= settings.tiktok_max_videos:
                        break

                    link_el = result.select_one("a.result__a")
                    if not link_el:
                        continue

                    href = link_el.get("href", "")
                    title = link_el.get_text(strip=True)

                    # DuckDuckGo redirect URL'sinden gerçek URL'i çıkar
                    actual_url = href
                    url_match = re.search(r'uddg=(https?[^&]+)', href)
                    if url_match:
                        actual_url = urllib.parse.unquote(url_match.group(1))

                    if "tiktok.com" not in actual_url:
                        continue
                    
                    # Aynı URL'i tekrar ekleme
                    if actual_url in seen_urls:
                        continue
                    seen_urls.add(actual_url)

                    # Snippet (açıklama)
                    snippet_el = result.select_one("a.result__snippet")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    # Video ID'yi URL'den çıkar
                    video_id_match = re.search(r'/video/(\d+)', actual_url)
                    video_id = video_id_match.group(1) if video_id_match else f"tiktok_{count}"

                    # Kullanıcı adı
                    author_match = re.search(r'@([a-zA-Z0-9_.]+)', actual_url)
                    author = author_match.group(1) if author_match else ""

                    description = f"{title}. {snippet}".strip()

                    if description:
                        results.append({
                            "platform": "tiktok",
                            "video_id": video_id,
                            "url": actual_url,
                            "description": description,
                            "author": author,
                            "transcript": description,
                        })
                        count += 1

        except Exception as e:
            logger.warning(f"[TikTok] Scraping failed: {e}")

        logger.success(f"[TikTok] Got {len(results)} videos")
        return results
