#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import threading
import os
import requests
import logging
from pathlib import Path
from datetime import datetime

# ===================== RENKLİ ÇIKTI =====================
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_colored(color, text):
    print(f"{color}{text}{Colors.NC}")

# ===================== LOG AYARLARI =====================
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ===================== SSH101.com AYARLARI =====================
RTMP_URL = "rtmp://ssh101.bozztv.com:1935/ssh101"

# ===================== YAYIN KONFIGÜRASYONLARI =====================
STREAMS = [
    {
        "name": "ZEM TV",
        "stream_url": "https://zemtv.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo.png",
        "logo_file": "logo_zemtv.png",
        "stream_key": "zemtv",
        "rtmp_server": f"{RTMP_URL}/zemtv",
        "max_retries": 10,
        "retry_delay": 5,
        "text_overlay": "t.me/zemmedya"  # Altta gösterilecek metin
    },
    {
        "name": "SAD SPOR",
        "stream_url": "https://sadspor.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo1.png",
        "logo_file": "logo_sadspor.png",
        "stream_key": "sadspor",
        "rtmp_server": f"{RTMP_URL}/sadspor",
        "max_retries": 10,
        "retry_delay": 5,
        "text_overlay": "t.me/zemmedya"
    },
    {
        "name": "GİZLİ BELGESEL",
        "stream_url": "https://gizlibelgesel.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo2.png",
        "logo_file": "logo_gizlibelgesel.png",
        "stream_key": "gizlibelgesel",
        "rtmp_server": f"{RTMP_URL}/gizlibelgesel",
        "max_retries": 10,
        "retry_delay": 5,
        "text_overlay": "t.me/zemmedya"
    }
]

# ===================== SİSTEM KONTROLÜ =====================
def is_termux():
    return 'TERMUX_VERSION' in os.environ or '/data/data/com.termux' in os.environ

def is_github_actions():
    return 'GITHUB_ACTIONS' in os.environ

def check_dependencies():
    print_colored(Colors.YELLOW, "[1/4] Bağımlılıklar kontrol ediliyor...")
    
    try:
        import requests
        print_colored(Colors.GREEN, "✅ requests paketi yüklü")
    except ImportError:
        print_colored(Colors.RED, "❌ requests paketi yüklü değil, yükleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print_colored(Colors.GREEN, "✅ FFmpeg yüklü")
    except:
        print_colored(Colors.RED, "❌ FFmpeg bulunamadı!")
        if is_termux():
            print_colored(Colors.YELLOW, "📦 FFmpeg yükleniyor... (pkg install ffmpeg)")
            subprocess.run(["pkg", "install", "-y", "ffmpeg"], check=True)
        else:
            print_colored(Colors.RED, "⚠️ Lütfen FFmpeg'i manuel olarak yükleyin")
            return False
    return True

# ===================== STREAM KAYNAĞINI KONTROL ET =====================
def check_stream_source(stream_url, stream_name):
    print_colored(Colors.YELLOW, f"[{stream_name}] Stream kaynağı kontrol ediliyor...")
    try:
        response = requests.get(stream_url, timeout=10)
        if response.status_code == 200:
            print_colored(Colors.GREEN, f"[{stream_name}] ✅ Stream kaynağı aktif")
            return True
        else:
            print_colored(Colors.RED, f"[{stream_name}] ❌ Stream kaynağı hata verdi (HTTP {response.status_code})")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"[{stream_name}] ❌ Stream kaynağına erişilemedi: {e}")
        return False

# ===================== LOGO'YU İNDİR =====================
def download_logo(stream_config):
    stream_name = stream_config['name']
    print_colored(Colors.YELLOW, f"[{stream_name}] Logo indiriliyor...")
    try:
        logo_url = stream_config['logo_url']
        logo_file = stream_config['logo_file']
        
        if logo_url.startswith('http'):
            response = requests.get(logo_url, timeout=30)
            response.raise_for_status()
            with open(logo_file, 'wb') as f:
                f.write(response.content)
            print_colored(Colors.GREEN, f"[{stream_name}] ✅ Logo indirildi: {logo_file}")
            return True
        elif os.path.exists(logo_url):
            print_colored(Colors.GREEN, f"[{stream_name}] ✅ Logo dosyası bulundu: {logo_url}")
            return True
        else:
            print_colored(Colors.RED, f"[{stream_name}] ❌ Logo bulunamadı!")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"[{stream_name}] ❌ Logo indirme hatası: {e}")
        logger.error(f"[{stream_name}] Logo indirme hatası: {e}")
        return False

# ===================== YAYIN BAŞLAT (TEK YAYIN) =====================
def start_stream(stream_config, stop_event, stream_status):
    stream_name = stream_config['name']
    stream_url = stream_config['stream_url']
    rtmp_server = stream_config['rtmp_server']
    logo_file = stream_config['logo_file']
    stream_key = stream_config['stream_key']
    text_overlay = stream_config.get('text_overlay', 't.me/zemmedya')
    max_retries = stream_config.get('max_retries', 10)
    retry_delay = stream_config.get('retry_delay', 5)
    
    stream_status[stream_name] = {
        'running': False,
        'error': None,
        'retry_count': 0
    }
    
    print_colored(Colors.YELLOW, f"[{stream_name}] Yayın hazırlanıyor...")
    
    if not check_stream_source(stream_url, stream_name):
        print_colored(Colors.RED, f"[{stream_name}] ❌ Stream kaynağı çalışmıyor!")
        stream_status[stream_name]['error'] = "Stream kaynağı çalışmıyor"
        return False
    
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, f"  {stream_name} Yayını Başlatılıyor")
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.BLUE, f"[{stream_name}] 📡 RTMP: {rtmp_server}")
    print_colored(Colors.BLUE, f"[{stream_name}] 📺 Stream: {stream_url}")
    print_colored(Colors.BLUE, f"[{stream_name}] 🌐 İzleme: https://ssh101.com/live/{stream_key}")
    print_colored(Colors.BLUE, f"[{stream_name}] 📱 HLS: https://lbgo.bozztv.com/ssh101/ssh101/{stream_key}/playlist.m3u8")
    print_colored(Colors.BLUE, f"[{stream_name}] 📝 Metin: {text_overlay}")
    print_colored(Colors.BLUE, "=" * 50)
    
    process = None
    retry_count = 0
    
    while not stop_event.is_set():
        try:
            if retry_count >= max_retries:
                print_colored(Colors.RED, f"[{stream_name}] ❌ Maksimum yeniden deneme sayısına ulaşıldı ({max_retries})")
                stream_status[stream_name]['error'] = f"Maksimum yeniden deneme ({max_retries})"
                break
            
            print_colored(Colors.GREEN, f"[{stream_name}] ▶ Yayınlanıyor: {stream_url}")
            logger.info(f"[{stream_name}] Yayınlanıyor: {stream_url}")
            
            logo_input = ['-i', logo_file] if os.path.exists(logo_file) else []
            
            # FFmpeg komutu - Logo kalıcı, alt metin t.me/zemmedya
            # buffer_size ve max_delay ile donmaları azalt
            command = [
                'ffmpeg',
                '-re',
                '-i', stream_url,
                '-fflags', 'nobuffer',
                '-flags', 'low_delay',
                '-max_delay', '0',
                '-analyzeduration', '1000000',
                '-probesize', '1000000',
            ] + logo_input + [
                '-filter_complex',
                '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setpts=PTS-STARTPTS[v0];'
                + ('' if not os.path.exists(logo_file) else '[1:v]scale=150:-1,format=rgba,colorchannelmixer=aa=1.0[logo];[v0][logo]overlay=W-w-15:15:format=auto,format=yuv420p[v1];' )
                + f'[v1]drawtext=text=\'{text_overlay}\':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.7:boxborderw=8:'
                + 'x=(w-text_w)/2:y=h-text_h-15:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf[v]',
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'medium',  # veryfast yerine medium - daha kaliteli
                '-tune', 'zerolatency',  # Düşük gecikme
                '-pix_fmt', 'yuv420p',
                '-b:v', '3000k',  # Biraz düşürüldü
                '-maxrate', '3000k',
                '-bufsize', '6000k',
                '-g', '120',  # GOP artırıldı
                '-c:a', 'aac',
                '-b:a', '96k',  # Ses bitrate düşürüldü
                '-ar', '44100',
                '-f', 'flv',
                '-flvflags', 'no_duration_filesize',
                rtmp_server
            ]
            
            process = subprocess.Popen(
                command, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                text=True
            )
            
            stream_status[stream_name]['running'] = True
            stream_status[stream_name]['error'] = None
            retry_count = 0
            
            # Yayın devam ederken bekle
            while not stop_event.is_set():
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    if process.returncode != 0:
                        print_colored(Colors.RED, f"[{stream_name}] ❌ FFmpeg hatası (kod: {process.returncode})")
                        if stderr:
                            print_colored(Colors.RED, f"[{stream_name}] Hata: {stderr[:300]}")
                        raise Exception(f"FFmpeg çıkış kodu: {process.returncode}")
                    
                    print_colored(Colors.YELLOW, f"[{stream_name}] ⏭ Stream yeniden başlatılıyor...")
                    break
                time.sleep(3)  # Daha sık kontrol
            
            if stop_event.is_set():
                if process:
                    process.terminate()
                    process.wait()
                break
            
            print_colored(Colors.BLUE, f"[{stream_name}] ⏳ Stream yeniden başlatılıyor...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            print_colored(Colors.RED, f"\n[{stream_name}] ⛔ Yayın durduruluyor...")
            if process:
                process.terminate()
                process.wait()
            print_colored(Colors.GREEN, f"[{stream_name}] ✅ Yayın sonlandırıldı.")
            stream_status[stream_name]['running'] = False
            break
        except Exception as e:
            retry_count += 1
            print_colored(Colors.RED, f"[{stream_name}] ❌ Yayın hatası (Deneme {retry_count}/{max_retries}): {e}")
            logger.error(f"[{stream_name}] Yayın hatası: {e}")
            
            stream_status[stream_name]['error'] = str(e)
            stream_status[stream_name]['running'] = False
            
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            
            print_colored(Colors.YELLOW, f"[{stream_name}] ⏳ {retry_delay} saniye sonra yeniden deneniyor...")
            time.sleep(retry_delay)
    
    stream_status[stream_name]['running'] = False
    logger.info(f"[{stream_name}] Yayın sonlandı")

# ===================== TÜM YAYINLARI BAŞLAT =====================
def start_all_streams():
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "  SSH101.com - 3'lü Yayın Sistemi (M3U8)")
    print_colored(Colors.BLUE, "=" * 50)
    
    if is_termux():
        print_colored(Colors.BLUE, "📱 Termux ortamı tespit edildi")
    elif is_github_actions():
        print_colored(Colors.BLUE, "☁️ GitHub Actions ortamı tespit edildi")
    else:
        print_colored(Colors.BLUE, "💻 Normal ortam tespit edildi")
    
    if not check_dependencies():
        print_colored(Colors.RED, "❌ Bağımlılıklar eksik, çıkılıyor...")
        return
    
    streams_data = []
    failed_streams = []
    
    for stream_config in STREAMS:
        print_colored(Colors.BLUE, f"\n{'='*30}")
        print_colored(Colors.BLUE, f"[{stream_config['name']}] Hazırlanıyor...")
        print_colored(Colors.BLUE, f"{'='*30}")
        
        if not download_logo(stream_config):
            print_colored(Colors.YELLOW, f"[{stream_config['name']}] ⚠️ Logo indirilemedi, yayın logosuz devam edecek.")
        
        if not check_stream_source(stream_config['stream_url'], stream_config['name']):
            print_colored(Colors.RED, f"[{stream_config['name']}] ❌ Stream kaynağı çalışmıyor! Bu yayın atlanıyor.")
            failed_streams.append(stream_config['name'])
            continue
        
        streams_data.append(stream_config)
    
    if len(streams_data) == 0:
        print_colored(Colors.RED, "❌ Hiçbir yayın başlatılamadı! Tüm kaynaklar hatalı.")
        return
    
    print_colored(Colors.GREEN, f"\n✅ {len(streams_data)} yayın hazır, başlatılıyor...")
    if failed_streams:
        print_colored(Colors.YELLOW, f"⚠️ {len(failed_streams)} yayın atlandı: {', '.join(failed_streams)}")
    
    print_colored(Colors.BLUE, "\n" + "=" * 50)
    print_colored(Colors.GREEN, f"✨ {len(streams_data)} yayın başlıyor! (Durdurmak için: Ctrl+C)")
    print_colored(Colors.BLUE, "=" * 50 + "\n")
    
    stop_event = threading.Event()
    threads = []
    stream_status = {}
    
    for stream_config in streams_data:
        stream_name = stream_config['name']
        thread = threading.Thread(
            target=start_stream,
            args=(stream_config, stop_event, stream_status),
            name=f"Thread-{stream_name}"
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        print_colored(Colors.BLUE, f"🔄 {stream_name} başlatıldı (Thread: {thread.name})")
        time.sleep(3)
    
    try:
        while True:
            time.sleep(60)
            print_colored(Colors.BLUE, "\n📊 Yayın Durum Raporu:")
            for stream_name, status in stream_status.items():
                status_text = "🟢 Çalışıyor" if status.get('running') else "🔴 DURDU"
                error_text = f" (Hata: {status.get('error')})" if status.get('error') else ""
                print_colored(Colors.BLUE, f"  {stream_name}: {status_text}{error_text}")
            
            active_threads = [t for t in threads if t.is_alive()]
            if len(active_threads) == 0:
                print_colored(Colors.RED, "\n❌ Tüm yayınlar durdu!")
                break
            
    except KeyboardInterrupt:
        print_colored(Colors.RED, "\n⛔ Tüm yayınlar durduruluyor...")
        stop_event.set()
        
        for thread in threads:
            thread.join(timeout=5)
        
        print_colored(Colors.GREEN, "✅ Tüm yayınlar sonlandırıldı.")
    
    print_colored(Colors.BLUE, "\n" + "=" * 50)
    print_colored(Colors.BLUE, "📊 FİNAL DURUM RAPORU")
    print_colored(Colors.BLUE, "=" * 50)
    for stream_name, status in stream_status.items():
        status_text = "✅ Çalıştı" if status.get('running') else "❌ DURDU"
        error_text = f" (Hata: {status.get('error')})" if status.get('error') else ""
        print_colored(Colors.BLUE, f"  {stream_name}: {status_text}{error_text}")
    print_colored(Colors.BLUE, "=" * 50)

# ===================== ANA FONKSİYON =====================
def main():
    try:
        start_all_streams()
    except Exception as e:
        print_colored(Colors.RED, f"❌ Beklenmeyen hata: {e}")
        logger.error(f"Beklenmeyen hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
