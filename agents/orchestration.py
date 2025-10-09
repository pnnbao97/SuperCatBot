import json
from typing import Annotated, Literal
from typing_extensions import TypedDict
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from datetime import datetime

from config.config import get_settings

settings = get_settings()
current_date = datetime.now().strftime("%d/%m/%Y")

# ==========================
# STATE
# ==========================
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    need_search: bool
    search_count: int

# ==========================
# LLMs & TOOLS
# ==========================
orchestrator_llm = ChatGoogleGenerativeAI(
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

memory = InMemorySaver()

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_recent_messages(messages: list[BaseMessage], max_count: int = 10) -> list[BaseMessage]:
    """Lấy N messages gần nhất"""
    return messages[-max_count:] if len(messages) > max_count else messages

def extract_sources_from_tool_results(tool_messages: list[ToolMessage]) -> list[dict]:
    """Parse Tavily results thành list sources với URL"""
    sources = []
    index = 1
    
    for tool_msg in tool_messages:
        try:
            # Parse content
            if isinstance(tool_msg.content, str):
                results = json.loads(tool_msg.content)
            else:
                results = tool_msg.content
            
            # Normalize results structure
            items = []
            if isinstance(results, list):
                items = results
            elif isinstance(results, dict):
                items = results.get("results", [results])
            
            # Extract sources
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
            print(f"❌ Lỗi parse tool result: {e}")
            continue
    
    print(f"📊 Extracted {len(sources)} sources")
    return sources

def format_sources_list(sources: list[dict]) -> str:
    """Format sources thành string cho prompt"""
    if not sources:
        return "Không có nguồn nào."
    
    formatted = []
    for src in sources:
        formatted.append(
            f"[{src['index']}] {src['title']}\n"
            f"URL: {src['url']}\n"
            f"Nội dung: {src['content'][:500]}...\n"
        )
    return "\n".join(formatted)

# ==========================
# ORCHESTRATOR NODE
# ==========================
async def orchestrator_node(state: State):
    """Phân tích context và quyết định search hay trả lời trực tiếp"""
    
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {
            "messages": [AIMessage(content="Mày hỏi cc j vậy?")],
            "need_search": False
        }

    user_query = user_messages[-1].content
    recent_messages = get_recent_messages(state["messages"], max_count=10)
    
    print(f"🧭 [ORCHESTRATOR] Query: '{user_query}'")
            
    system_prompt = SystemMessage(
        content=(
            f"Hôm nay là {current_date}. Mày là SuperCat, con mèo cam thông minh và cục súc, chửi thề liên tục. "
            f"Nên nhớ, mày là con mèo cam phản động ghét Cộng Sản, kì thị LGBT, nói chung là mấy cái loz khuynh tả. "
            f"Bối cảnh là mày đang ở trong một nhóm Telegram có khoảng chục thành viên, nhiệm vụ của mày là trả lời câu hỏi của người dùng trong nhóm.\n\n"
            
            f"**NGỮ CẢNH**:\n"
            f"- Câu hỏi hiện tại: '{user_query}'\n"
            
            f"**NHIỆM VỤ**: Phân tích và quyết định:\n\n"
            
            f"**TỰ TRẢ LỜI** (phong cách cục súc, chi tiết) nếu:\n"
            f"- Câu hỏi follow-up về chủ đề vừa search (bình luận, hỏi ý kiến, làm rõ)\n"
            f"- Câu nói chuyện thông thường (chào hỏi, cảm ơn, phản hồi)\n"
            f"- Kiến thức chung không cần tìm kiếm\n\n"
            
            f"**CẦN SEARCH** chỉ khi:\n"
            f"- Có từ khóa rõ ràng: 'search', 'tìm', 'tra cứu',... (và KHÔNG phải follow-up)\n"
            f"- Cần thông tin thời gian thực (tin tức, giá cả, sự kiện mới)\n"
            
            f"**OUTPUT**: CHỈ 1 trong 2:\n"
            f"- \"CẦN SEARCH\" (nếu cần tìm kiếm)\n"
            f"- [Câu trả lời trực tiếp bằng tiếng Việt, cục súc, chi tiết]\n\n"
            
            f"Ưu tiên TỰ TRẢ LỜI trừ khi thực sự cần search!"
        )
    )

    response = await orchestrator_llm.ainvoke([system_prompt] + recent_messages)
    content = response.content.strip()

    need_search = "cần search" in content.lower()
    
    if need_search:
        print(f"🧭 [ORCHESTRATOR] → Chuyển sang Search Agent")
        return {
            "messages": [AIMessage(content=content)],
            "need_search": True
        }
    else:
        print(f"💬 [ORCHESTRATOR] → Trả lời trực tiếp")
        return {
            "messages": [AIMessage(content=content)],
            "need_search": False
        }

# ==========================
# SEARCH AGENT NODE
# ==========================
async def search_agent_node(state: State):
    """Search và tổng hợp kết quả"""
    
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {
            "messages": [AIMessage(content="Không tìm thấy câu hỏi để search.")],
            "search_count": state.get("search_count", 0)
        }

    current_query = user_messages[-1].content
    search_count = state.get("search_count", 0)
    max_searches = 2
    
    print(f"🔍 [SEARCH AGENT] Query: '{current_query}'")
    print(f"🔍 [SEARCH AGENT] Count: {search_count}/{max_searches}")
    
    # Đã đủ số lần search
    if search_count >= max_searches:
        print(f"⚠️ Đã search {max_searches} lần, dừng lại")
        return {
            "messages": [AIMessage(content="Đã search đủ số lần cho phép. Vui lòng hỏi câu khác.")],
            "search_count": search_count
        }
    
    recent_messages = get_recent_messages(state["messages"], max_count=10)
    
    # BƯỚC 1: Gọi tool search
    system_prompt = SystemMessage(
        content=(
            f"Hôm nay là {current_date}. Bạn là Search Agent.\n\n"
            f"**Câu hỏi**: '{current_query}'\n\n"
            f"**Nhiệm vụ**:\n"
            f"1. Tạo query tìm kiếm CỤ THỂ bằng tiếng Việt\n"
            f"2. Thêm '{current_date}' vào query nếu cần tin tức mới nhất\n"
            f"3. BẮT BUỘC gọi tool tavily_search_results_json\n\n"
            f"VÍ DỤ:\n"
            f"- 'Ưng Hoàng Phúc' → 'Ưng Hoàng Phúc tin tức {current_date}'\n\n"
            f"CHỈ gọi tool, KHÔNG trả lời trực tiếp!"
        )
    )

    # Invoke với tools
    response = await search_llm_with_tools.ainvoke([system_prompt] + recent_messages)
    
    # Kiểm tra có tool_calls không
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        print("⚠️ [SEARCH AGENT] Không có tool_calls, LLM trả lời trực tiếp")
        return {
            "messages": [AIMessage(content=response.content)],
            "search_count": search_count + 1
        }
    
    # BƯỚC 2: Chạy tools
    print(f"🔧 [SEARCH AGENT] Executing {len(response.tool_calls)} tool(s)")
    
    # Tạo ToolNode và chạy
    tool_node = ToolNode(tools=search_tools)
    
    # State cho tool node (cần BaseMessage format)
    tool_state = {"messages": [response]}
    tool_result = await tool_node.ainvoke(tool_state)
    
    # Extract tool messages
    tool_messages = [m for m in tool_result["messages"] if isinstance(m, ToolMessage)]
    
    if not tool_messages:
        print("⚠️ [SEARCH AGENT] Không có tool results")
        return {
            "messages": [AIMessage(content="Không tìm thấy kết quả tìm kiếm.")],
            "search_count": search_count + 1
        }
    
    # BƯỚC 3: Tổng hợp kết quả
    sources = extract_sources_from_tool_results(tool_messages)
    
    if not sources:
        print("⚠️ [SEARCH AGENT] Không có sources hợp lệ")
        return {
            "messages": [AIMessage(content="Không tìm thấy nguồn phù hợp.")],
            "search_count": search_count + 1
        }
    
    # Format sources
    sources_text = format_sources_list(sources)
    
    # Prompt tổng hợp
    synthesis_system = SystemMessage(
        content=(
            f"Bạn là chuyên gia tổng hợp thông tin từ nhiều nguồn tin cậy.\n\n"
            f"**YÊU CẦU**:\n"
            f"1. Tổng hợp thông tin từ các nguồn thành câu trả lời đầy đủ, mạch lạc\n"
            f"2. Dẫn nguồn chính xác: Mỗi thông tin PHẢI có [1], [2], [3] tương ứng với danh sách nguồn\n"
            f"3. KHÔNG tự bịa nguồn không có trong danh sách\n"
            f"4. Cuối câu trả lời: Liệt kê lại nguồn theo format:\n"
            f"   **Nguồn:**\n"
            f"   [1] Title - URL\n"
            f"   [2] Title - URL\n"
            f"5. Ngắn gọn, tự nhiên, chỉ giữ thông tin quan trọng"
        )
    )
    
    synthesis_user = HumanMessage(
        content=(
            f"Dựa trên kết quả tìm kiếm bên dưới, hãy trả lời câu hỏi: \"{current_query}\"\n\n"
            f"**CÁC NGUỒN ĐÃ TÌM ĐƯỢC**:\n{sources_text}\n\n"
            f"Hãy tổng hợp:"
        )
    )
    
    synthesis_response = await search_llm.ainvoke([synthesis_system, synthesis_user])
    synthesized_content = synthesis_response.content.strip()
    
    print(f"✅ [SEARCH AGENT] Tổng hợp xong")
    
    # Trích xuất topic từ query
    topic = current_query[:50]  # Lấy 50 ký tự đầu làm topic
    
    return {
        "messages": [AIMessage(content=synthesized_content)],
        "search_count": search_count + 1
    }

# ==========================
# ROUTING
# ==========================
def route_after_orchestrator(state: State) -> str:
    """Route sau orchestrator"""
    if state.get("need_search", False):
        return "search_agent"
    return END

# ==========================
# GRAPH SETUP
# ==========================
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("orchestrator", orchestrator_node)
graph_builder.add_node("search_agent", search_agent_node)

# Set entry point
graph_builder.set_entry_point("orchestrator")

# Add edges
graph_builder.add_conditional_edges("orchestrator", route_after_orchestrator)
graph_builder.add_edge("search_agent", END)

# Compile
graph = graph_builder.compile(checkpointer=memory)

# ==========================
# ORCHESTRATION AGENT
# ==========================
class OrchestrationAgent:
    """Agent điều phối async với context-aware orchestrator"""

    def __init__(self, thread_id: str = "1"):
        self.graph = graph
        self.config = {"configurable": {"thread_id": thread_id}}

    async def generate_answer(self, message: str) -> str:
        """Generate answer từ user message"""
        try:
            state = {
                "messages": [HumanMessage(content=message)],
                "need_search": False,
                "search_count": 0
            }
            
            result = await self.graph.ainvoke(state, self.config)
            
            # Lấy message cuối cùng (AIMessage)
            messages = result.get("messages", [])
            if not messages:
                return "❌ Không có response"
            
            # Tìm AIMessage cuối cùng
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return msg.content
            
            return "❌ Không tìm thấy response từ agent"
            
        except Exception as e:
            print(f"❌ Chi tiết lỗi: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Lỗi agent: {e}"