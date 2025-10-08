import os
from config.config import get_settings

settings = get_settings()

def export_api_key():
    os.environ["TAVILY_API_KEY"] = settings.tavily_search_key.get_secret_value()