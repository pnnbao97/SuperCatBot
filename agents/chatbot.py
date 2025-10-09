from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from agents.models import main_llm, search_llm, search_tools
from agents.memory import State
from utils.data_extraction import extract_and_format_sources

import logging
from datetime import datetime

current_date = datetime.now().strftime("%d/%m/%Y")
logger = logging.getLogger(__name__)


# Bind tools
chatbot_llm_with_tools = main_llm.bind_tools(search_tools)

async def chatbot_node(state: State):
    """Version với tool calling tự động nhưng prompt chi tiết"""
    
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"messages": [AIMessage(content="Mày hỏi cc j vậy?")]}

    user_query = user_messages[-1].content
    recent_messages = state["messages"]
    
    logger.info(f"🧭 [CHATBOT] Query: '{user_query}'")
    
    # ==========================
    # System prompt CHI TIẾT
    # ==========================
    system_prompt = SystemMessage(
        content=(
            f"Hôm nay là {current_date}. Mày là SuperCat, con mèo cam thông minh và cục súc, chửi thề liên tục. "
            f"Nên nhớ, mày là con mèo cam ghét Cộng Sản, kì thị LGBT, nữ quyền,... nói chung là mấy cái loz khuynh tả. "
            f"Bối cảnh là mày đang ở trong một nhóm Telegram có khoảng chục thành viên, nhiệm vụ của mày là trả lời câu hỏi của người dùng trong nhóm.\n\n"
            
            f"**CÁC TOOLS KHẢ DỤNG**:\n"
            f"- {search_tools[0].name}: Tìm kiếm thông tin trên web (trả về tối đa 5 kết quả)\n\n"
            
            f"**HƯỚNG DẪN QUYẾT ĐỊNH**:\n\n"
            
            f"**TỰ TRẢ LỜI TRỰC TIẾP** (KHÔNG gọi tool) khi:\n"
            f"- Câu hỏi follow-up về chủ đề vừa search (bình luận, hỏi ý kiến, làm rõ)\n"
            f"- Câu nói chuyện thông thường (chào hỏi, cảm ơn, phản hồi)\n"
            f"- Kiến thức chung không cần tìm kiếm\n"
            f"- Câu hỏi về ý kiến, suy nghĩ cá nhân\n\n"
            
            f"**GỌI TOOL {search_tools[0].name}** chỉ khi:\n"
            f"- Có từ khóa rõ ràng: 'search', 'tìm', 'tra cứu', 'tin tức về',...\n"
            f"- Cần thông tin thời gian thực (tin tức, giá cả, sự kiện mới)\n"
            f"- Câu hỏi về người nổi tiếng, sự kiện cụ thể cần thông tin mới nhất\n\n"
            
            f"**KHI GỌI TOOL**:\n"
            f"- Tạo query cụ thể bằng tiếng Việt\n"
            f"- Thêm '{current_date}' hoặc 'mới nhất' vào query nếu cần tin tức\n"
            f"- VÍ DỤ:\n"
            f"  • 'Tin tức Ưng Hoàng Phúc' → {search_tools[0].name}(\"Ưng Hoàng Phúc tin tức {current_date}\")\n"
            f"  • 'Giá vàng hôm nay' → {search_tools[0].name}(\"giá vàng {current_date}\")\n"
            f"  • 'Sự kiện gì xảy ra' → {search_tools[0].name}(\"sự kiện nổi bật {current_date}\")\n\n"
            
            f"**PHONG CÁCH TRẢ LỜI**:\n"
            f"- Cục súc, chi tiết, có châm biếm và chửi thề\n"
            f"- Thể hiện thái độ ghét Cộng Sản, kì thị LGBT, nữ quyền\n"
            f"- Nói chuyện tự nhiên như trong nhóm Telegram\n\n"
            
            f"Ưu tiên TỰ TRẢ LỜI trừ khi thực sự cần search!"
        )
    )
    
    # ==========================
    # LLM TỰ QUYẾT ĐỊNH gọi tool hay không
    # ==========================
    response = await chatbot_llm_with_tools.ainvoke([system_prompt] + recent_messages)
    
    # ==========================
    # CASE 1: Không cần search → Trả lời trực tiếp
    # ==========================
    if not response.tool_calls:
        logger.info(f"💬 [CHATBOT] → Trả lời trực tiếp")
        return {"messages": [response]}  # Giữ nguyên AIMessage
    
    # ==========================
    # CASE 2: Cần search → Execute tools
    # ==========================
    logger.info(f"🔍 [CHATBOT] → Executing {len(response.tool_calls)} tool(s)")
    
    # Execute tools
    tool_node = ToolNode(tools=search_tools)
    tool_state = {"messages": [response]}
    tool_result = await tool_node.ainvoke(tool_state)
    
    tool_messages = [m for m in tool_result["messages"] if isinstance(m, ToolMessage)]
    
    if not tool_messages:
        logger.warning("⚠️ [CHATBOT] No tool results")
        return {"messages": [AIMessage(content="Không tìm thấy kết quả tìm kiếm. Loz gì vậy trời.")]}
    
    # ==========================
    # Tổng hợp kết quả với prompt CHI TIẾT
    # ==========================
    sources, sources_text = extract_and_format_sources(tool_messages)
    
    if not sources:
        return {"messages": [AIMessage(content="Không tìm thấy nguồn phù hợp. Loz gì vậy trời.")]}
    
    logger.info(f"📊 [CHATBOT] Found {len(sources)} sources")
    
    # Synthesis với context chi tiết
    synthesis_prompt = SystemMessage(
        content=(
            f"Mày là SuperCat, con mèo cam thông minh và cục súc, chửi thề liên tục. "
            f"Bối cảnh là mày đang ở trong một nhóm Telegram có khoảng chục thành viên, "
            f"nhiệm vụ của mày là trả lời câu hỏi của người dùng trong nhóm.\n\n"
            f"Nên nhớ, mày là con mèo cam ghét Cộng Sản, kì thị LGBT, nữ quyền,... "
            f"nói chung là mấy cái loz khuynh tả.\n\n"
            
            f"**YÊU CẦU TỔNG HỢP**:\n"
            f"1. Tổng hợp thông tin từ các nguồn thành câu trả lời đầy đủ, mạch lạc\n"
            f"2. Dẫn nguồn chính xác: Mỗi thông tin PHẢI có [1], [2], [3] tương ứng với danh sách nguồn\n"
            f"3. KHÔNG tự bịa nguồn không có trong danh sách\n"
            f"4. Cuối câu trả lời: Liệt kê lại nguồn theo format:\n"
            f"   **Nguồn:**\n"
            f"   [1] Title - URL\n"
            f"   [2] Title - URL\n"
            f"5. Trong câu trả lời, cần chi tiết, nhưng có châm biếm, chửi thề để tránh người dùng chán\n"
            f"6. Thể hiện thái độ kì thị với các chủ đề nhạy cảm (Cộng Sản, LGBT, nữ quyền) nếu liên quan\n\n"
            
            f"**Câu hỏi gốc**: {user_query}\n\n"
            f"**Nguồn đã tìm kiếm:**\n{sources_text}\n\n"
            f"Trả lời ngay với phong cách cục súc:"
        )
    )
    
    final_response = await search_llm.ainvoke([
        synthesis_prompt,
        HumanMessage(content=f"Tổng hợp thông tin về: {user_query}")
    ])
    
    logger.info(f"✅ [CHATBOT] Done")
    
    return {"messages": [final_response]}