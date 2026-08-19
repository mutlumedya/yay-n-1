#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import threading
import os
import requests
import re
from pathlib import Path

# ===================== RENKLİ ÇIKTI =====================
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(color, text):
    print(f"{color}{text}{Colors.NC}")

# ===================== SSH101.com AYARLARI =====================
RTMP_URL = "rtmp://ssh101.bozztv.com:1935/ssh101"
STREAM_KEY = "mutlu1"
rtmp_server = f"{RTMP_URL}/{STREAM_KEY}"

# ===================== M3U KAYNAĞI =====================
M3U_SOURCE = "https://raw.githubusercontent.com/Sonuiptvnew/Sonuiptvnew/5d4cca3c9e8258373feeaf556b1a9e58bc4cf32e/xxx%20(1).m3u"  # Veya başka bir M3U linki
LOGO_URL = "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo.png"

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

# ===================== M3U'YU İŞLE =====================
def m3u_dan_linkleri_cek(m3u_url):
    """M3U dosyasından video linklerini çıkar"""
    print_colored(Colors.YELLOW, "[2/5] M3U dosyası işleniyor...")
    
    try:
        # URL'den indir
        if m3u_url.startswith('http'):
            print_colored(Colors.BLUE, f"📥 M3U indiriliyor: {m3u_url}")
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
            print_colored(Colors.YELLOW, "⚠️ Video linki bulunamadı, tüm linkler deneniyor...")
            tum_linkler = re.findall(r'https?://[^\s"]+', m3u_icerik)
            video_linkleri = [link for link in tum_linkler if not link.endswith('.m3u')]
        
        print_colored(Colors.GREEN, f"✅ {len(video_linkleri)} video linki bulundu!")
        return video_linkleri
        
    except Exception as e:
        print_colored(Colors.RED, f"❌ M3U işleme hatası: {e}")
        return []

# ===================== LOGO'YU İNDİR =====================
def download_logo():
    """Logo dosyasını indir"""
    print_colored(Colors.YELLOW, "[3/5] Logo indiriliyor...")
    try:
        # Logo URL'sini kontrol et
        if LOGO_URL.startswith('http'):
            response = requests.get(LOGO_URL, timeout=30)
            response.raise_for_status()
            with open('logo.png', 'wb') as f:
                f.write(response.content)
            print_colored(Colors.GREEN, "✅ Logo indirildi")
            return True
        elif os.path.exists(LOGO_URL):
            print_colored(Colors.GREEN, "✅ Logo dosyası bulundu")
            return True
        else:
            print_colored(Colors.RED, "❌ Logo bulunamadı!")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"❌ Logo indirme hatası: {e}")
        return False

# ===================== YAYIN BAŞLAT =====================
def start_stream(video_list):
    """Yayını başlat"""
    print_colored(Colors.YELLOW, "[4/5] Yayın hazırlanıyor...")
    
    if len(video_list) == 0:
        print_colored(Colors.RED, "❌ Yayın için video bulunamadı!")
        return False
    
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "  SSH101.com Yayın Başlatılıyor")
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.BLUE, f"📡 RTMP: {rtmp_server}")
    print_colored(Colors.BLUE, f"🎬 Video Sayısı: {len(video_list)}")
    print_colored(Colors.BLUE, f"🌐 İzleme: https://ssh101.com/live/{STREAM_KEY}")
    print_colored(Colors.BLUE, f"📱 HLS: https://lbgo.bozztv.com/ssh101/ssh101/{STREAM_KEY}/playlist.m3u8")
    print_colored(Colors.BLUE, "=" * 50)
    
    # Yayın döngüsü
    video_index = 0
    while True:
        try:
            video_url = video_list[video_index]
            print_colored(Colors.GREEN, f"▶ Yayınlanıyor [{video_index+1}/{len(video_list)}]: {video_url}")
            
            # Logo var mı kontrol et
            logo_input = ['-i', 'logo.png'] if os.path.exists('logo.png') else []
            
            # FFmpeg komutu oluştur
            command = [
                'ffmpeg',
                '-re',
                '-i', video_url,
            ] + logo_input + [
                '-filter_complex',
                '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black[v0];'
                + ('' if not os.path.exists('logo.png') else '[1:v]scale=200:-1[logo];[v0][logo]overlay=W-w-5:3')
                + ',drawtext=text=\'SSH101.com\':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.6:boxborderw=5:x=(w-text_w)/2:y=h-text_h-20[v]',
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
            process = subprocess.Popen(command)
            
            # Yayın bitene kadar bekle
            while True:
                time.sleep(5)
                if process.poll() is not None:
                    print_colored(Colors.YELLOW, f"⏭ Video bitti [{video_index+1}/{len(video_list)}]")
                    break
            
            # Sıradaki videoya geç
            video_index = (video_index + 1) % len(video_list)
            print_colored(Colors.BLUE, "⏳ Sıradaki videoya geçiliyor...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            print_colored(Colors.RED, "\n⛔ Yayın durduruluyor...")
            if 'process' in locals():
                process.terminate()
                process.wait()
            print_colored(Colors.GREEN, "✅ Yayın sonlandırıldı.")
            break
        except Exception as e:
            print_colored(Colors.RED, f"❌ Yayın hatası: {e}")
            print_colored(Colors.YELLOW, "⏳ 5 saniye sonra yeniden deneniyor...")
            time.sleep(5)
            video_index = (video_index + 1) % len(video_list)

# ===================== ANA FONKSİYON =====================
def main():
    """Ana program"""
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "  SSH101.com Yayın Sistemi")
    print_colored(Colors.BLUE, "=" * 50)
    
    # Ortam bilgisi
    if is_termux():
        print_colored(Colors.BLUE, "📱 Termux ortamı tespit edildi")
    elif is_github_actions():
        print_colored(Colors.BLUE, "☁️ GitHub Actions ortamı tespit edildi")
    else:
        print_colored(Colors.BLUE, "💻 Normal ortam tespit edildi")
    
    # 1. Bağımlılıkları kontrol et
    check_dependencies()
    
    # 2. M3U'dan video linklerini al
    playlist = []
    
    # Önce M3U kaynağını dene
    if M3U_SOURCE:
        playlist = m3u_dan_linkleri_cek(M3U_SOURCE)
    
    # M3U başarısız olursa yerel playlist.m3u'yu dene
    if len(playlist) == 0 and os.path.exists('playlist.m3u'):
        print_colored(Colors.YELLOW, "⚠️ Yerel playlist.m3u deneniyor...")
        playlist = m3u_dan_linkleri_cek('playlist.m3u')
    
    # Hala boşsa hata ver
    if len(playlist) == 0:
        print_colored(Colors.RED, "❌ Yayın için hiç video bulunamadı!")
        print_colored(Colors.YELLOW, "📝 Lütfen M3U_SOURCE değişkenini güncelleyin veya playlist.m3u dosyası oluşturun")
        sys.exit(1)
    
    # 3. Logo'yu indir
    download_logo()
    
    # 4. Yayını başlat
    print_colored(Colors.YELLOW, "[5/5] Yayın başlatılıyor...")
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "✨ Yayın başlıyor! (Durdurmak için: Ctrl+C)")
    print_colored(Colors.BLUE, "=" * 50)
    
    start_stream(playlist)

if __name__ == "__main__":
    main()
