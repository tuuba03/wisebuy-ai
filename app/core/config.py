from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = "YOUR_GEMINI_API_KEY"
    serpapi_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ai_max_tokens: int = 2048
    
    scraper_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    scraper_timeout: int = 20
    youtube_max_videos: int = 5
    tiktok_max_videos: int = 4

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()
