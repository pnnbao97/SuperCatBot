import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import argparse
import re
from typing import Optional, Tuple, Dict, List
from urllib.parse import urlparse
from pytubefix import YouTube

class MultiPlatformExtractor:
    def __init__(self):
        self.temp_dir = None
        self.output_dir = Path("videos")
        self.output_dir.mkdir(exist_ok=True)
        
        # Danh sách các nền tảng được hỗ trợ
        self.supported_platforms = {
            'youtube.com': 'YouTube',
            'youtu.be': 'YouTube',
            'facebook.com': 'Facebook',
            'fb.watch': 'Facebook',
            'reddit.com': 'Reddit',
            'twitter.com': 'X (Twitter)',
            'x.com': 'X (Twitter)',
            'tiktok.com': 'TikTok',
            'instagram.com': 'Instagram',
            'vimeo.com': 'Vimeo',
            'dailymotion.com': 'Dailymotion'
        }
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Xác định nền tảng từ URL"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Loại bỏ www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Kiểm tra từng nền tảng
            for platform_domain, platform_name in self.supported_platforms.items():
                if platform_domain in domain:
                    return platform_name
            
            return None
        except Exception:
            return None
    
    def is_youtube_url(self, url: str) -> bool:
        """Kiểm tra xem URL có phải YouTube không"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain in ['youtube.com', 'youtu.be']
        except Exception:
            return False
    
    def parse_time(self, time_str: str) -> int:
        """Chuyển đổi thời gian từ format MM:SS hoặc HH:MM:SS thành giây"""
        time_str = time_str.strip()
        
        # Format MM:SS
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            minutes, seconds = map(int, time_str.split(':'))
            return minutes * 60 + seconds
        
        # Format HH:MM:SS
        elif re.match(r'^\d{1,2}:\d{2}:\d{2}$', time_str):
            hours, minutes, seconds = map(int, time_str.split(':'))
            return hours * 3600 + minutes * 60 + seconds
        
        # Format chỉ có giây
        elif re.match(r'^\d+$', time_str):
            return int(time_str)
        
        else:
            raise ValueError(f"Format thời gian không hợp lệ: {time_str}")
    
    def download_youtube_with_pytubefix(self, url: str, audio_only: bool = False) -> Optional[str]:
        """Tải YouTube video/audio bằng pytubefix"""
        try:
            print(f"📥 Đang tải từ YouTube bằng pytubefix: {url}")
            
            # Tạo thư mục tạm
            self.temp_dir = tempfile.mkdtemp()
            
            # Tạo YouTube object
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
            
            print(f"📺 Tiêu đề: {yt.title}")
            print(f"⏱️ Thời lượng: {yt.length} giây")
            
            if audio_only:
                # Tải audio
                print("🎵 Đang tải audio...")
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                if not audio_stream:
                    print("❌ Không tìm thấy stream audio")
                    return None
                    
                downloaded_file = audio_stream.download(output_path=self.temp_dir)
                
                # Chuyển đổi sang MP3 nếu cần
                if not downloaded_file.endswith('.mp3'):
                    try:
                        print("fhasdofj")
                        # Sử dụng ffmpeg để convert sang mp3
                        output_file = os.path.join(f"{yt.title}.wav")
                        output_file = re.sub(r'[<>:"/\\|?*]', '_', output_file)
                        
                        cmd = [
                            'ffmpeg', '-i', downloaded_file,
                            '-acodec', 'pcm_s16le',  # codec chuẩn của wav
                            '-ar', '24000',          # (tùy chọn) đặt sample rate
                            '-ac', '1',              # (tùy chọn) mono
                            '-y', output_file
                        ]
                        subprocess.run(cmd, capture_output=True, check=True)
                        
                        # Xóa file gốc và sử dụng file mp3
                        os.remove(downloaded_file)
                        downloaded_file = output_file
                        
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("⚠️ Không thể convert sang MP3, giữ nguyên định dạng gốc")
                
            else:
                # Tải video
                print("🎬 Đang tải video...")
                
                video_stream = yt.streams.get_highest_resolution()
                downloaded_file = video_stream.download(output_path=self.temp_dir)
            
            if downloaded_file and os.path.exists(downloaded_file):
                file_size = Path(downloaded_file).stat().st_size / (1024 * 1024)
                print(f"✅ Tải thành công: {os.path.basename(downloaded_file)}")
                print(f"📁 Kích thước file: {file_size:.2f} MB")
                return downloaded_file
            else:
                print("❌ Không tải được file")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi tải từ YouTube: {e}")
            return None
    
    def download_with_ytdlp(self, url: str, audio_only: bool = False) -> Optional[str]:
        """Tải video/audio từ các nền tảng khác bằng yt-dlp"""
        try:
            # Xác định nền tảng
            platform = self.detect_platform(url)
            if not platform:
                print(f"❌ Không hỗ trợ nền tảng này: {url}")
                return None
            
            mode = "audio" if audio_only else "video"
            print(f"📥 Đang tải {mode} từ {platform} bằng yt-dlp: {url}")
            
            # Tạo thư mục tạm
            self.temp_dir = tempfile.mkdtemp()
            
            # Lệnh yt-dlp cơ bản
            cmd = [
                'yt-dlp',
                '--output', os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
                '--no-playlist'
            ]
            
            # Thêm tùy chọn audio hoặc video
            if audio_only:
                cmd.extend([
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0'  # Chất lượng cao nhất
                ])
            else:
                format_attempts: List[Tuple[List[str], str, str]] = [
                    # 1) Lấy best tự nhiên (không ép container)
                    ([
                        '--format', 'bestvideo[height<=720][ext=mp4][vcodec^=avc]+bestaudio/best[ext=mp4]',
                    ], '*', 'ưu tiên mp4'),
                    # 2) Ghép bestvideo+bestaudio và để yt-dlp tự chọn container
                    ([
                        '--format', 'bestvideo*+bestaudio/best'
                    ], '*', 'bestvideo+bestaudio (giữ nguyên định dạng)'),
                ]
                format_attempts_to_use = format_attempts
            
            # Thêm URL cuối cùng
            if audio_only:
                cmd.append(url)
                print("⏳ Đang tải...")
                subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                downloaded_files = list(Path(self.temp_dir).glob('*.mp3'))
                if not downloaded_files:
                    downloaded_files = [f for f in Path(self.temp_dir).iterdir()
                                        if f.is_file() and not f.name.endswith('.part')]
                if downloaded_files:
                    downloaded_file = str(downloaded_files[0])
                    file_size = Path(downloaded_file).stat().st_size / (1024 * 1024)
                    print(f"✅ Tải thành công: {os.path.basename(downloaded_file)}")
                    print(f"📁 Kích thước file: {file_size:.2f} MB")
                    return downloaded_file
                print("❌ Không tìm thấy file đã tải")
                return None

            for fmt_args, pattern, label in format_attempts_to_use:
                attempt_cmd = cmd + fmt_args + [url]
                print(f"⏳ Đang tải (chiến lược: {label})...")
                try:
                    subprocess.run(
                        attempt_cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    # Tìm file đã tải theo pattern
                    downloaded_files = list(Path(self.temp_dir).glob(pattern)) if pattern != '*' else \
                        [f for f in Path(self.temp_dir).iterdir() if f.is_file() and not f.name.endswith('.part')]
                    if downloaded_files:
                        downloaded_file = str(downloaded_files[0])
                        file_size = Path(downloaded_file).stat().st_size / (1024 * 1024)
                        print(f"✅ Tải thành công: {os.path.basename(downloaded_file)}")
                        print(f"📁 Kích thước file: {file_size:.2f} MB")
                        return downloaded_file
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Thất bại với chiến lược '{label}'. Thử phương án khác...")
                    continue

            # Nếu tất cả chiến lược đều thất bại
            print("❌ Không thể tải với các định dạng chuẩn.")
            return None
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Lỗi khi tải: {e}")
            if e.stderr:
                print(f"Chi tiết lỗi: {e.stderr}")
            return None
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")
            return None
    
    def download_video(self, url: str, audio_only: bool = False) -> Optional[str]:
        """Tải video MP4 hoặc audio MP3 từ nhiều nền tảng"""
        # Kiểm tra nếu là YouTube thì dùng pytubefix, còn lại dùng yt-dlp
        if self.is_youtube_url(url):
            return self.download_youtube_with_pytubefix(url, audio_only)
        else:
            return self.download_with_ytdlp(url, audio_only)
    
    def extract_segment(self, input_file: str, start_time: int, 
                       end_time: int, output_filename: str, is_audio: bool = False) -> bool:
        """Tách đoạn video hoặc audio từ file gốc"""
        try:
            # Kiểm tra ffmpeg
            try:
                subprocess.run(['ffmpeg', '-version'], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ ffmpeg không được cài đặt. Không thể tách đoạn.")
                print("Vui lòng cài đặt ffmpeg: https://ffmpeg.org/download.html")
                return False
            
            duration = end_time - start_time
            
            # Đường dẫn file output
            extension = '.mp3' if is_audio else '.mp4'
            output_path = self.output_dir / f"{output_filename}{extension}"
            
            content_type = "audio" if is_audio else "video"
            print(f"✂️ Đang tách {content_type} từ {start_time}s đến {end_time}s...")
            
            # Lệnh ffmpeg để tách
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',  # Copy không re-encode để giữ chất lượng
                '-y',  # Overwrite file nếu tồn tại
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                print(f"✅ Tách thành công: {output_path}")
                print(f"📁 Kích thước file: {file_size:.2f} MB")
                print(f"⏱️ Thời lượng: {duration} giây")
                return True
            else:
                print("❌ Không tạo được file output")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Lỗi khi tách {content_type}: {e}")
            if e.stderr:
                print(f"Chi tiết lỗi: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")
            return False
    
    def move_to_output(self, source_file: str, output_filename: Optional[str] = None) -> bool:
        """Di chuyển file từ temp sang thư mục output"""
        try:
            source_path = Path(source_file)
            
            if output_filename:
                # Giữ nguyên extension gốc
                extension = source_path.suffix
                output_path = self.output_dir / f"{output_filename}{extension}"
            else:
                output_path = self.output_dir / source_path.name
            
            # Copy file sang thư mục output
            shutil.copy2(source_file, output_path)
            
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                print(f"📁 File đã lưu: {output_path}")
                print(f"📏 Kích thước: {file_size:.2f} MB")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Lỗi khi lưu file: {e}")
            return False
    
    def cleanup(self):
        """Dọn dẹp file tạm"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("🧹 Đã dọn dẹp file tạm")
    
    def process(self, url: str, audio_only: bool = False, start_time: Optional[str] = None, 
               end_time: Optional[str] = None, output_filename: Optional[str] = None) -> bool:
        """Xử lý toàn bộ quy trình"""
        try:
            # Kiểm tra logic thời gian
            has_time_params = start_time is not None and end_time is not None
            
            if has_time_params:
                try:
                    start_seconds = self.parse_time(start_time)
                    end_seconds = self.parse_time(end_time)
                except ValueError as e:
                    print(f"❌ {e}")
                    return False
                
                if start_seconds >= end_seconds:
                    print("❌ Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc")
                    return False
                
                # Thông báo chế độ tách đoạn
                content_type = "audio" if audio_only else "video"
                print(f"✂️ Chế độ tách đoạn {content_type} được kích hoạt")
            
            # Tải video/audio
            downloaded_file = self.download_video(url, audio_only)
            if not downloaded_file:
                return False
            
            # Xử lý theo chế độ
            if has_time_params:
                # Tách đoạn video/audio
                if not output_filename:
                    video_title = os.path.splitext(os.path.basename(downloaded_file))[0]
                    content_type = "audio" if audio_only else "video"
                    output_filename = f"{video_title}_{content_type}_segment_{start_time}_{end_time}"
                    # Loại bỏ ký tự không hợp lệ trong tên file
                    output_filename = re.sub(r'[<>:"/\\|?*]', '_', output_filename)
                
                success = self.extract_segment(
                    downloaded_file, start_seconds, end_seconds, output_filename, audio_only
                )
            else:
                # Lưu toàn bộ file
                success = self.move_to_output(downloaded_file, output_filename)
            
            return success
            
        finally:
            self.cleanup()

def main():
    parser = argparse.ArgumentParser(
        description="Tải video/audio từ nhiều nền tảng với khả năng tách đoạn audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:

Tải toàn bộ video MP4 (mặc định):
  python script.py "https://youtube.com/watch?v=VIDEO_ID"
  
Tải toàn bộ audio MP3:
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -a
  
Tách đoạn video MP4:
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -s "1:30" -e "2:45"
  
Tách đoạn audio MP3:
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -a -s "1:30" -e "2:45"
  
Với tên file tùy chỉnh:
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -o "my_video"
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -a -o "my_audio"
  python script.py "https://youtube.com/watch?v=VIDEO_ID" -s "90" -e "165" -o "my_segment"

Format thời gian:
  - MM:SS (ví dụ: 1:30, 2:45)  
  - HH:MM:SS (ví dụ: 1:30:45)
  - Chỉ số giây (ví dụ: 90, 165)

Các nền tảng được hỗ trợ:
  YouTube (pytubefix), Facebook, Reddit, X(Twitter), TikTok, Instagram, Vimeo, Dailymotion (yt-dlp)
        """
    )
    
    parser.add_argument('url', help='URL video từ bất kỳ nền tảng nào được hỗ trợ')
    parser.add_argument('-a', '--audio-only', action='store_true', 
                       help='Chỉ tải audio (mặc định là tải video)')
    parser.add_argument('-s', '--start', help='Thời gian bắt đầu để tách audio (MM:SS, HH:MM:SS, hoặc số giây)')
    parser.add_argument('-e', '--end', help='Thời gian kết thúc để tách audio (MM:SS, HH:MM:SS, hoặc số giây)')
    parser.add_argument('-o', '--output', help='Tên file output (không cần extension)')
    
    args = parser.parse_args()
    
    # Kiểm tra tham số thời gian
    if (args.start and not args.end) or (args.end and not args.start):
        print("❌ Cần cung cấp cả thời gian bắt đầu (-s) và kết thúc (-e)")
        sys.exit(1)
    
    # Tạo extractor và xử lý
    extractor = MultiPlatformExtractor()
    success = extractor.process(
        args.url, 
        args.audio_only, 
        args.start, 
        args.end, 
        args.output
    )
    
    if success:
        print(f"\n🎉 Hoàn thành! File đã được lưu trong thư mục '{extractor.output_dir}'")
    else:
        print("\n❌ Có lỗi xảy ra trong quá trình xử lý")
        sys.exit(1)

if __name__ == "__main__":
    main()