from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from config.config import get_settings

settings = get_settings()

main_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=settings.gemini_api_key.get_secret_value(),
    temperature=0.4,
)

search_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=settings.gemini_api_key.get_secret_value(),
    temperature=0.2,
)

search_tool = TavilySearch(max_results=5)
search_tools = [search_tool]
search_llm_with_tools = search_llm.bind_tools(search_tools)