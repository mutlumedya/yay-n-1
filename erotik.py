#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import threading
import os
import requests
import re
import logging
from pathlib import Path
from datetime import datetime

# ===================== RENKLİ ÇIKTI =====================
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(color, text):
    print(f"{color}{text}{Colors.NC}")

# ===================== LOG AYARLARI =====================
def setup_logging():
    """Log dosyası oluştur"""
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
        "m3u_url": "https://zemtv.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo.png",
        "logo_file": "logo_zemtv.png",
        "stream_key": "zemtv",
        "rtmp_server": f"{RTMP_URL}/zemtv",
        "max_retries": 5,  # Maksimum yeniden deneme sayısı
        "retry_delay": 10  # Yeniden deneme arası bekleme (saniye)
    },
    {
        "name": "SAD SPOR",
        "m3u_url": "https://sadspor.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo1.png",
        "logo_file": "logo_sadspor.png",
        "stream_key": "sadspor",
        "rtmp_server": f"{RTMP_URL}/sadspor",
        "max_retries": 5,
        "retry_delay": 10
    },
    {
        "name": "GİZLİ BELGESEL",
        "m3u_url": "https://gizlibelgesel.mutlumedya.workers.dev/playlist.m3u8",
        "logo_url": "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo2.png",
        "logo_file": "logo_gizlibelgesel.png",
        "stream_key": "gizlibelgesel",
        "rtmp_server": f"{RTMP_URL}/gizlibelgesel",
        "max_retries": 5,
        "retry_delay": 10
    }
]

# ===================== SİSTEM KONTROLÜ =====================
def is_termux():
    """Termux ortamında mı çalışıyor kontrol et"""
    return 'TERMUX_VERSION' in os.environ or '/data/data/com.termux' in os.environ

def is_github_actions():
    """GitHub Actions ortamında mı çalışıyor kontrol et"""
    return 'GITHUB_ACTIONS' in os.environ

def check_dependencies():
    """Gerekli bağımlılıkları kontrol et"""
    print_colored(Colors.YELLOW, "[1/5] Bağımlılıklar kontrol ediliyor...")
    
    # Python paketleri
    try:
        import requests
        print_colored(Colors.GREEN, "✅ requests paketi yüklü")
    except ImportError:
        print_colored(Colors.RED, "❌ requests paketi yüklü değil, yükleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    
    # FFmpeg kontrolü
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

# ===================== M3U'YU İŞLE =====================
def m3u_dan_linkleri_cek(m3u_url, stream_name):
    """M3U dosyasından video linklerini çıkar"""
    print_colored(Colors.YELLOW, f"[{stream_name}] M3U dosyası işleniyor...")
    
    try:
        # URL'den indir
        if m3u_url.startswith('http'):
            print_colored(Colors.BLUE, f"[{stream_name}] 📥 M3U indiriliyor: {m3u_url}")
            response = requests.get(m3u_url, timeout=30)
            response.raise_for_status()
            m3u_icerik = response.text
        else:
            # Yerel dosya
            with open(m3u_url, 'r', encoding='utf-8') as f:
                m3u_icerik = f.read()
        
        # Video linklerini ayıkla
        video_linkleri = []
        satirlar = m3u_icerik.split('\n')
        
        for i, satir in enumerate(satirlar):
            satir = satir.strip()
            # #EXTINF bilgilerini sakla (isteğe bağlı)
            if satir.startswith('#EXTINF'):
                continue
            # Video linklerini kontrol et
            if satir.startswith('http'):
                # Video uzantılarını kontrol et
                video_uzantilari = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.mov', '.flv']
                if any(uzanti in satir.lower() for uzanti in video_uzantilari):
                    video_linkleri.append(satir)
                # M3U içindeki diğer linkler (playlist olmayan)
                elif not satir.endswith('.m3u'):
                    video_linkleri.append(satir)
        
        # Eğer hiç link bulunamadıysa, tüm http linklerini al
        if len(video_linkleri) == 0:
            print_colored(Colors.YELLOW, f"[{stream_name}] ⚠️ Video linki bulunamadı, tüm linkler deneniyor...")
            tum_linkler = re.findall(r'https?://[^\s"]+', m3u_icerik)
            video_linkleri = [link for link in tum_linkler if not link.endswith('.m3u')]
        
        print_colored(Colors.GREEN, f"[{stream_name}] ✅ {len(video_linkleri)} video linki bulundu!")
        return video_linkleri
        
    except Exception as e:
        print_colored(Colors.RED, f"[{stream_name}] ❌ M3U işleme hatası: {e}")
        logger.error(f"[{stream_name}] M3U işleme hatası: {e}")
        return []

# ===================== LOGO'YU İNDİR =====================
def download_logo(stream_config):
    """Logo dosyasını indir"""
    stream_name = stream_config['name']
    print_colored(Colors.YELLOW, f"[{stream_name}] Logo indiriliyor...")
    try:
        logo_url = stream_config['logo_url']
        logo_file = stream_config['logo_file']
        
        # Logo URL'sini kontrol et
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
def start_stream(stream_config, video_list, stop_event, stream_status):
    """Tek bir yayını başlat - Bağımsız çalışır"""
    stream_name = stream_config['name']
    rtmp_server = stream_config['rtmp_server']
    logo_file = stream_config['logo_file']
    stream_key = stream_config['stream_key']
    max_retries = stream_config.get('max_retries', 5)
    retry_delay = stream_config.get('retry_delay', 10)
    
    # Stream durumunu güncelle
    stream_status[stream_name] = {
        'running': False,
        'error': None,
        'retry_count': 0
    }
    
    print_colored(Colors.YELLOW, f"[{stream_name}] Yayın hazırlanıyor...")
    
    if len(video_list) == 0:
        print_colored(Colors.RED, f"[{stream_name}] ❌ Yayın için video bulunamadı!")
        stream_status[stream_name]['error'] = "Video bulunamadı"
        return False
    
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, f"  {stream_name} Yayını Başlatılıyor")
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.BLUE, f"[{stream_name}] 📡 RTMP: {rtmp_server}")
    print_colored(Colors.BLUE, f"[{stream_name}] 🎬 Video Sayısı: {len(video_list)}")
    print_colored(Colors.BLUE, f"[{stream_name}] 🌐 İzleme: https://ssh101.com/live/{stream_key}")
    print_colored(Colors.BLUE, f"[{stream_name}] 📱 HLS: https://lbgo.bozztv.com/ssh101/ssh101/{stream_key}/playlist.m3u8")
    print_colored(Colors.BLUE, "=" * 50)
    
    # Yayın döngüsü
    video_index = 0
    process = None
    retry_count = 0
    
    while not stop_event.is_set():
        try:
            # Eğer maksimum deneme sayısına ulaşıldıysa, bu yayını durdur
            if retry_count >= max_retries:
                print_colored(Colors.RED, f"[{stream_name}] ❌ Maksimum yeniden deneme sayısına ulaşıldı ({max_retries})")
                stream_status[stream_name]['error'] = f"Maksimum yeniden deneme ({max_retries})"
                break
            
            video_url = video_list[video_index]
            print_colored(Colors.GREEN, f"[{stream_name}] ▶ Yayınlanıyor [{video_index+1}/{len(video_list)}]: {video_url}")
            logger.info(f"[{stream_name}] Yayınlanıyor: {video_url}")
            
            # Logo var mı kontrol et
            logo_input = ['-i', logo_file] if os.path.exists(logo_file) else []
            
            # FFmpeg komutu oluştur
            command = [
                'ffmpeg',
                '-re',
                '-i', video_url,
            ] + logo_input + [
                '-filter_complex',
                '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black[v0];'
                + ('' if not os.path.exists(logo_file) else f'[1:v]scale=200:-1[logo];[v0][logo]overlay=W-w-5:3')
                + f',drawtext=text=\'{stream_name}\':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.6:boxborderw=5:x=(w-text_w)/2:y=h-text_h-20[v]',
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-pix_fmt', 'yuv420p',
                '-b:v', '4000k',
                '-maxrate', '4000k',
                '-bufsize', '8000k',
                '-g', '50',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '44100',
                '-f', 'flv',
                rtmp_server
            ]
            
            # Yayını başlat
            process = subprocess.Popen(
                command, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                text=True
            )
            
            # Stream çalışıyor olarak işaretle
            stream_status[stream_name]['running'] = True
            stream_status[stream_name]['error'] = None
            retry_count = 0  # Başarılı başlatıldı, retry sayısını sıfırla
            
            # Yayın bitene kadar bekle veya durdurma sinyali gelene kadar
            while not stop_event.is_set():
                if process.poll() is not None:
                    # FFmpeg çıktısını kontrol et
                    stdout, stderr = process.communicate()
                    if process.returncode != 0:
                        print_colored(Colors.RED, f"[{stream_name}] ❌ FFmpeg hatası (kod: {process.returncode})")
                        if stderr:
                            print_colored(Colors.RED, f"[{stream_name}] Hata: {stderr[:200]}")
                        raise Exception(f"FFmpeg çıkış kodu: {process.returncode}")
                    
                    print_colored(Colors.YELLOW, f"[{stream_name}] ⏭ Video bitti [{video_index+1}/{len(video_list)}]")
                    break
                time.sleep(5)
            
            # Eğer durdurma sinyali geldiyse çık
            if stop_event.is_set():
                if process:
                    process.terminate()
                    process.wait()
                break
            
            # Sıradaki videoya geç
            video_index = (video_index + 1) % len(video_list)
            print_colored(Colors.BLUE, f"[{stream_name}] ⏳ Sıradaki videoya geçiliyor...")
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
            
            # Sıradaki videoya geç
            video_index = (video_index + 1) % len(video_list)
    
    # Stream durumunu güncelle
    stream_status[stream_name]['running'] = False
    logger.info(f"[{stream_name}] Yayın sonlandı")

# ===================== TÜM YAYINLARI BAŞLAT =====================
def start_all_streams():
    """Tüm yayınları paralel olarak başlat"""
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "  SSH101.com - 3'lü Yayın Sistemi")
    print_colored(Colors.BLUE, "=" * 50)
    
    # Ortam bilgisi
    if is_termux():
        print_colored(Colors.BLUE, "📱 Termux ortamı tespit edildi")
    elif is_github_actions():
        print_colored(Colors.BLUE, "☁️ GitHub Actions ortamı tespit edildi")
    else:
        print_colored(Colors.BLUE, "💻 Normal ortam tespit edildi")
    
    # Bağımlılıkları kontrol et
    if not check_dependencies():
        print_colored(Colors.RED, "❌ Bağımlılıklar eksik, çıkılıyor...")
        return
    
    # Her yayın için M3U'yu işle ve logoyu indir
    streams_data = []
    failed_streams = []
    
    for stream_config in STREAMS:
        print_colored(Colors.BLUE, f"\n{'='*30}")
        print_colored(Colors.BLUE, f"[{stream_config['name']}] Hazırlanıyor...")
        print_colored(Colors.BLUE, f"{'='*30}")
        
        # M3U'dan video linklerini al
        playlist = m3u_dan_linkleri_cek(stream_config['m3u_url'], stream_config['name'])
        
        if len(playlist) == 0:
            print_colored(Colors.RED, f"[{stream_config['name']}] ❌ Yayın için hiç video bulunamadı! Bu yayın atlanıyor.")
            failed_streams.append(stream_config['name'])
            continue
        
        # Logo'yu indir
        if not download_logo(stream_config):
            print_colored(Colors.YELLOW, f"[{stream_config['name']}] ⚠️ Logo indirilemedi, yayın logosuz devam edecek.")
        
        streams_data.append({
            'config': stream_config,
            'playlist': playlist
        })
    
    if len(streams_data) == 0:
        print_colored(Colors.RED, "❌ Hiçbir yayın başlatılamadı! Tüm kaynaklar hatalı.")
        return
    
    print_colored(Colors.GREEN, f"\n✅ {len(streams_data)} yayın hazır, başlatılıyor...")
    if failed_streams:
        print_colored(Colors.YELLOW, f"⚠️ {len(failed_streams)} yayın atlandı: {', '.join(failed_streams)}")
    
    # Tüm yayınları paralel başlat
    print_colored(Colors.BLUE, "\n" + "=" * 50)
    print_colored(Colors.GREEN, f"✨ {len(streams_data)} yayın başlıyor! (Durdurmak için: Ctrl+C)")
    print_colored(Colors.BLUE, "Yayın durumları aşağıda takip edilebilir:")
    print_colored(Colors.BLUE, "=" * 50 + "\n")
    
    stop_event = threading.Event()
    threads = []
    stream_status = {}  # Her yayının durumunu takip et
    
    for stream_data in streams_data:
        stream_name = stream_data['config']['name']
        thread = threading.Thread(
            target=start_stream,
            args=(stream_data['config'], stream_data['playlist'], stop_event, stream_status),
            name=f"Thread-{stream_name}"
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        print_colored(Colors.BLUE, f"🔄 {stream_name} başlatıldı (Thread: {thread.name})")
        time.sleep(3)  # Her yayın arasında 3 saniye bekleyelim
    
    # Yayın durumlarını takip et
    try:
        while True:
            # Her 30 saniyede bir durum raporu
            time.sleep(30)
            print_colored(Colors.BLUE, "\n📊 Yayın Durum Raporu:")
            for stream_name, status in stream_status.items():
                status_text = "🟢 Çalışıyor" if status.get('running') else "🔴 DURDU"
                error_text = f" (Hata: {status.get('error')})" if status.get('error') else ""
                print_colored(Colors.BLUE, f"  {stream_name}: {status_text}{error_text}")
            
            # Çalışan thread sayısını kontrol et
            active_threads = [t for t in threads if t.is_alive()]
            if len(active_threads) == 0:
                print_colored(Colors.RED, "\n❌ Tüm yayınlar durdu!")
                break
            
    except KeyboardInterrupt:
        print_colored(Colors.RED, "\n⛔ Tüm yayınlar durduruluyor...")
        stop_event.set()
        
        # Thread'lerin bitmesini bekle
        for thread in threads:
            thread.join(timeout=5)
        
        print_colored(Colors.GREEN, "✅ Tüm yayınlar sonlandırıldı.")
    
    # Final durum raporu
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
    """Ana program"""
    try:
        start_all_streams()
    except Exception as e:
        print_colored(Colors.RED, f"❌ Beklenmeyen hata: {e}")
        logger.error(f"Beklenmeyen hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
