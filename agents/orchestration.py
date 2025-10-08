import asyncio
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

from config.config import get_settings

settings = get_settings()

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    need_search: bool

# ==========================
# ⚡ LLMs
# ==========================
orchestrator_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=settings.gemini_api_key.get_secret_value(),
    temperature=0.4,
)

search_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=settings.gemini_api_key.get_secret_value(),
    temperature=0.2,
)

search_tool = TavilySearch(max_results=3)
search_tools = [search_tool]
search_llm_with_tools = search_llm.bind_tools(search_tools)

# ==========================
# ⚡ Memory
# ==========================
class CleanMemorySaver(InMemorySaver):
    def __init__(self, max_messages: int = 50):
        super().__init__()
        self.max_messages = max_messages

    def put(self, config, state, *args, **kwargs):
        try:
            msgs = state.get("messages", [])
            if isinstance(msgs, list):
                filtered = [m for m in msgs if isinstance(m, (HumanMessage, AIMessage))]
                state["messages"] = filtered[-self.max_messages:]
        except Exception as e:
            print(f"[CleanMemorySaver] warning: {e}")
        return super().put(config, state, *args, **kwargs)

memory = CleanMemorySaver(max_messages=50)

def clean_chat_history(messages, max_messages=6):
    """
    Trích xuất lịch sử chat gọn gàng cho LLM.
    Giữ tối đa `max_messages` tin nhắn gần đây.
    Loại bỏ metadata thừa, chỉ giữ nội dung.
    """
    recent = messages[-max_messages:]
    cleaned = []
    for m in recent:
        if isinstance(m, HumanMessage):
            cleaned.append(HumanMessage(content=m.content))
        elif isinstance(m, AIMessage):
            cleaned.append(AIMessage(content=m.content))
        elif hasattr(m, "type") and m.type == "tool":
            # Chuyển ToolMessage thành AIMessage tóm tắt nội dung tool
            summary = f"[Tool {getattr(m, 'name', 'unknown')}] {str(m.content)[:500]}"
            cleaned.append(AIMessage(content=summary))
        # Bỏ qua các loại message khác hoặc unknown
    return cleaned

# ==========================
# ⚡ Helper: logic search
# ==========================
def should_search(query: str) -> bool:
    query_lower = query.lower()
    explicit_keywords = ["search", "tìm kiếm", "tra cứu", "google", "tìm giúp", "kiếm giúp", "tra giúp", "tìm thông tin", "tìm tin"]
    time_sensitive_keywords = ["tin tức", "tin mới", "mới nhất", "vừa xảy ra", "hôm nay", "hôm qua", "tuần này", "tháng này", "hiện tại", "bây giờ", "lúc này"]
    general_knowledge = ["là gì", "định nghĩa", "giải thích", "cách thức", "tại sao", "làm thế nào", "ví dụ về", "so sánh", "khác nhau", "giống nhau"]

    if any(kw in query_lower for kw in explicit_keywords):
        return True
    if any(kw in query_lower for kw in general_knowledge):
        return False
    if any(kw in query_lower for kw in time_sensitive_keywords):
        return True
    return False

# ==========================
# ⚡ Async nodes
# ==========================
async def orchestrator_node(state: State):
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"messages": [AIMessage(content="Xin lỗi, tôi không nhận được câu hỏi.")]}

    user_query = user_messages[-1].content

    if should_search(user_query):
        print(f"🧭 [KEYWORD MATCH] Điều phối → Search Agent với query: {user_query}")
        return {"messages": [AIMessage(content="Đang tìm kiếm thông tin...")], "need_search": True}

    recent_messages = clean_chat_history(state["messages"], max_messages=6)
    print(f"🧭 [CONTEXT] Điều phối → Context: {recent_messages}")

    system_prompt = SystemMessage(
        content=(
            "Bạn là một trợ lý AI hữu ích. Đọc lịch sử hội thoại để hiểu ngữ cảnh.\n\n"
            "CHỈ trả lời 'CẦN SEARCH' nếu câu hỏi THỰC SỰ cần dữ liệu thời gian thực, "
            "ví dụ: giá cổ phiếu hiện tại, kết quả bóng đá hôm nay, tai nạn mới xảy ra.\n\n"
            "VỚI TẤT CẢ các câu hỏi khác, hãy trả lời trực tiếp bằng tiếng Việt.\n"
            "CHỈ trả lời 'CẦN SEARCH' hoặc trả lời câu hỏi trực tiếp."
        )
    )

    response = await orchestrator_llm.ainvoke([system_prompt] + recent_messages)
    content = response.content.strip()

    if "cần search" in content.lower():
        print(f"🧭 [LLM CONFIRM] Điều phối → Search Agent với query: {user_query}")
        return {"messages": [AIMessage(content="Đang tìm kiếm thông tin...")], "need_search": True}

    print(f"💬 Điều phối → Trả lời trực tiếp: {content[:60]}...")
    return {"messages": [response], "need_search": False}


async def search_agent_node(state: State):
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"messages": [AIMessage(content="Không tìm thấy câu hỏi để tìm kiếm.")]}

    recent_messages = clean_chat_history(state["messages"], max_messages=6)

    system_prompt = SystemMessage(
        content=(
            "Bạn là một trợ lý chuyên tìm kiếm thông tin thời gian thực TẠI VIỆT NAM.\n"
            "Tạo query tìm kiếm đầy đủ và cụ thể, sử dụng công cụ tavily_search_results_json.\n"
            "Tóm tắt kết quả bằng tiếng Việt."
        )
    )

    response = await search_llm_with_tools.ainvoke([system_prompt] + recent_messages)
    print(f"🔍 Search Agent response: {response}")
    return {"messages": [response]}


async def process_tool_results(state: State):
    """Process tool results"""
    print("🧭 [PROCESS TOOL RESULTS] Đang xử lý kết quả từ tools...")
    
    # Lấy tool messages
    tool_messages = [m for m in state["messages"] if hasattr(m, 'type') and m.type == 'tool']
    
    if not tool_messages:
        return {"messages": [AIMessage(content="Không tìm thấy kết quả tìm kiếm.")]}
    
    # Lấy user query ban đầu
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    original_query = user_messages[-1].content if user_messages else ""
    
    # Tổng hợp kết quả
    system_prompt = SystemMessage(
        content=(
            f"Dựa trên kết quả tìm kiếm bên dưới, hãy trả lời câu hỏi: '{original_query}' "
            "như một chuyên gia tổng hợp và phân tích thông tin, trích dẫn nguồn nếu có thể (nguồn là đường link url)."
        )
    )
    
    final_response = await search_llm.ainvoke([system_prompt] + state["messages"][-5:])
    
    print(f"💬 Câu trả lời cuối: {final_response}")
    return {"messages": [final_response]}
# ==========================
# ⚡ Graph setup
# ==========================
graph_builder = StateGraph(State)
graph_builder.add_node("orchestrator", orchestrator_node)
graph_builder.add_node("search_agent", search_agent_node)
graph_builder.add_node("process_results", process_tool_results)

tool_node = ToolNode(tools=search_tools)
graph_builder.add_node("tools", tool_node)

def route_after_orchestrator(state: State) -> str:
    return "search_agent" if state.get("need_search", False) else END

def route_after_search(state: State) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

graph_builder.set_entry_point("orchestrator")
graph_builder.add_conditional_edges("orchestrator", route_after_orchestrator)
graph_builder.add_conditional_edges("search_agent", route_after_search)
graph_builder.add_edge("tools", "process_results")
graph_builder.add_edge("process_results", END)

graph = graph_builder.compile(checkpointer=memory)

# ==========================
# ⚡ OrchestrationAgent async
# ==========================
class OrchestrationAgent:
    """Agent điều phối async với multi-agent và memory giới hạn."""

    def __init__(self, thread_id: str = "1"):
        self.graph = graph
        self.config = {"configurable": {"thread_id": thread_id}}

    async def generate_answer(self, message: str):
        try:
            state = {"messages": [HumanMessage(content=message)], "need_search": False}
            result = await self.graph.ainvoke(state, self.config)
            return result["messages"][-1].content
        except Exception as e:
            print(f"❌ Chi tiết lỗi: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Lỗi agent: {e}"
