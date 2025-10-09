import json
from langchain_core.messages import ToolMessage
import logging

logger = logging.getLogger(__name__)

def extract_and_format_sources(tool_messages: list[ToolMessage]) -> tuple[list[dict], str]:
    """Parse Tavily results và format thành string"""
    sources = []
    index = 1
    
    for tool_msg in tool_messages:
        try:
            results = json.loads(tool_msg.content)
            items = results.get("results", [results])
            
            for item in items:
                if isinstance(item, dict) and item.get("url"):
                    sources.append({
                        "index": index,
                        "title": item.get("title", "Nguồn không có tiêu đề"),
                        "url": item["url"],
                        "content": item.get("content", "")
                    })
                    index += 1
                    
        except Exception as e:
            logger.error(f"❌ Lỗi parse tool result: {e}")
            continue
    
    # Format sources
    if not sources:
        return sources, "Không có nguồn nào."
    
    formatted = []
    for src in sources:
        formatted.append(
            f"[{src['index']}] {src['title']}\n"
            f"URL: {src['url']}\n"
            f"Nội dung: {src['content'][:500]}...\n"
        )
   
    logger.info(f"📊 Extracted {len(sources)} sources")
    return sources, "\n".join(formatted)