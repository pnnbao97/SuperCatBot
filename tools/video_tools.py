from langchain_core.tools import tool
from typing import Optional
import logging
from utils.yt_downloader import MultiPlatformExtractor

logger = logging.getLogger(__name__)

@tool
async def download_video(
    url: str,
    audio_only: bool = False,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    output_filename: Optional[str] = None
) -> str:
    """
    Tải video hoặc audio từ các nền tảng (YouTube, Facebook, TikTok, etc.)
    
    Args:
        url: URL của video (YouTube, Facebook, TikTok, Instagram, Reddit, X, Vimeo, Dailymotion)
        audio_only: True nếu chỉ tải audio (MP3), False nếu tải video (MP4)
        start_time: Thời gian bắt đầu để tách đoạn (format: MM:SS hoặc HH:MM:SS hoặc số giây)
        end_time: Thời gian kết thúc để tách đoạn (format: MM:SS hoặc HH:MM:SS hoặc số giây)
        output_filename: Tên file output tùy chỉnh (không cần extension)
    
    Returns:
        Thông báo kết quả download và đường dẫn file
    
    Examples:
        - Tải toàn bộ video: download_video("https://youtube.com/watch?v=xxx")
        - Tải audio: download_video("https://youtube.com/watch?v=xxx", audio_only=True)
        - Tách đoạn video: download_video("https://youtube.com/watch?v=xxx", start_time="1:30", end_time="2:45")
        - Tách đoạn audio: download_video("https://youtube.com/watch?v=xxx", audio_only=True, start_time="90", end_time="165")
    """
    try:
        # Khởi tạo extractor
        extractor = MultiPlatformExtractor()
        
        # Xác định nền tảng
        platform = extractor.detect_platform(url)
        if not platform:
            return f"❌ URL không được hỗ trợ: {url}"
        
        logger.info(f"📥 Đang tải từ {platform}: {url}")
        
        # Xử lý download
        success = extractor.process(
            url=url,
            audio_only=audio_only,
            start_time=start_time,
            end_time=end_time,
            output_filename=output_filename
        )
        
        if success:
            content_type = "audio MP3" if audio_only else "video MP4"
            mode = "Tách đoạn" if start_time and end_time else "Tải toàn bộ"
            
            result = f"✅ {mode} {content_type} thành công!\n"
            result += f"📁 File đã lưu trong thư mục: {extractor.output_dir}\n"
            
            if start_time and end_time:
                result += f"⏱️ Từ {start_time} đến {end_time}"
            
            return result
        else:
            return f"❌ Không thể tải {content_type} từ {url}"
            
    except Exception as e:
        logger.error(f"❌ Lỗi download_video: {e}")
        return f"❌ Lỗi: {str(e)}"


@tool
async def get_video_info(url: str) -> str:
    """
    Lấy thông tin về video (tiêu đề, thời lượng, nền tảng)
    
    Args:
        url: URL của video
    
    Returns:
        Thông tin chi tiết về video
    """
    try:
        extractor = MultiPlatformExtractor()
        
        # Xác định nền tảng
        platform = extractor.detect_platform(url)
        if not platform:
            return f"❌ URL không được hỗ trợ: {url}"
        
        # Nếu là YouTube, lấy thông tin chi tiết
        if extractor.is_youtube_url(url):
            from pytubefix import YouTube
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
            
            info = f"📺 **Thông tin video**\n"
            info += f"- Nền tảng: YouTube\n"
            info += f"- Tiêu đề: {yt.title}\n"
            info += f"- Thời lượng: {yt.length} giây ({yt.length // 60}:{yt.length % 60:02d})\n"
            info += f"- Tác giả: {yt.author}\n"
            info += f"- Lượt xem: {yt.views:,}\n"
            
            return info
        else:
            return f"📺 Video từ nền tảng: {platform}\nURL: {url}"
            
    except Exception as e:
        logger.error(f"❌ Lỗi get_video_info: {e}")
        return f"❌ Không thể lấy thông tin video: {str(e)}"


# Danh sách tools để bind vào LLM
video_tools = [download_video, get_video_info]