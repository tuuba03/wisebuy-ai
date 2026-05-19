class ScrapingException(Exception):
    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"Scraping failed for {source}: {reason}")

class AIAnalysisException(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"AI Analysis failed: {reason}")

class VideoTranscriptException(Exception):
    def __init__(self, video_id: str, reason: str):
        self.video_id = video_id
        self.reason = reason
        super().__init__(f"Could not fetch transcript for {video_id}: {reason}")
