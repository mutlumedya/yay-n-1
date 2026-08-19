#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import threading
import os
import requests
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

# ===================== 3 YAYIN =====================
# Yayın 1 - ZEM TV
STREAM_URL1 = "https://zemtv.mutlumedya.workers.dev/playlist.m3u8"
LOGO_URL1 = "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo.png"
LOGO_FILE1 = "logo_zemtv.png"
STREAM_KEY1 = "zemtv"
RTMP_SERVER1 = f"{RTMP_URL}/{STREAM_KEY1}"
TEXT1 = "t.me/zemmedya"

# Yayın 2 - SAD SPOR
STREAM_URL2 = "https://cdn.codenet.lol/streamgo/stremgo123/4866.m3u8"
LOGO_URL2 = "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/Photo.png"
LOGO_FILE2 = "logo_sadspor.png"
STREAM_KEY2 = "sadspor"
RTMP_SERVER2 = f"{RTMP_URL}/{STREAM_KEY2}"
TEXT2 = "t.me/zemmedya"

# Yayın 3 - GİZLİ BELGESEL
STREAM_URL3 = "https://gizlibelgesel.mutlumedya.workers.dev/playlist.m3u8"
LOGO_URL3 = "https://raw.githubusercontent.com/mutlumedya/yay-n-1/refs/heads/main/logo2.png"
LOGO_FILE3 = "logo_gizlibelgesel.png"
STREAM_KEY3 = "gizlibelgesel"
RTMP_SERVER3 = f"{RTMP_URL}/{STREAM_KEY3}"
TEXT3 = "t.me/zemmedya"

# ===================== SİSTEM KONTROLÜ =====================
def is_termux():
    return 'TERMUX_VERSION' in os.environ or '/data/data/com.termux' in os.environ

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
            print_colored(Colors.YELLOW, "📦 FFmpeg yükleniyor...")
            subprocess.run(["pkg", "install", "-y", "ffmpeg"], check=True)
        else:
            print_colored(Colors.RED, "⚠️ FFmpeg kur amk")
            return False
    return True

# ===================== STREAM KONTROL =====================
def check_stream_source(stream_url, name):
    print_colored(Colors.YELLOW, f"[{name}] Stream kontrol...")
    try:
        response = requests.get(stream_url, timeout=10)
        if response.status_code == 200:
            print_colored(Colors.GREEN, f"[{name}] ✅ Aktif")
            return True
        else:
            print_colored(Colors.RED, f"[{name}] ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"[{name}] ❌ {e}")
        return False

# ===================== LOGO İNDİR =====================
def download_logo(logo_url, logo_file, name):
    print_colored(Colors.YELLOW, f"[{name}] Logo indiriliyor...")
    try:
        if logo_url.startswith('http'):
            response = requests.get(logo_url, timeout=30)
            response.raise_for_status()
            with open(logo_file, 'wb') as f:
                f.write(response.content)
            print_colored(Colors.GREEN, f"[{name}] ✅ Logo indi")
            return True
        else:
            print_colored(Colors.RED, f"[{name}] ❌ Logo yok")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"[{name}] ❌ Logo hatası: {e}")
        return False

# ===================== YAYIN BAŞLAT =====================
def start_stream(stream_url, logo_file, rtmp_server, stream_key, text, name):
    print_colored(Colors.YELLOW, f"[{name}] Yayın hazırlanıyor...")
    
    if not check_stream_source(stream_url, name):
        print_colored(Colors.RED, f"[{name}] ❌ Stream ölü!")
        return
    
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, f"  {name} Yayını Başlıyor")
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.BLUE, f"[{name}] 📡 RTMP: {rtmp_server}")
    print_colored(Colors.BLUE, f"[{name}] 📺 İzle: https://ssh101.com/live/{stream_key}")
    print_colored(Colors.BLUE, "=" * 50)
    
    process = None
    retry_count = 0
    
    while True:
        try:
            print_colored(Colors.GREEN, f"[{name}] ▶ Yayınlanıyor...")
            
            logo_input = ['-i', logo_file] if os.path.exists(logo_file) else []
            
            command = [
                'ffmpeg',
                '-re',
                '-i', stream_url,
                '-fflags', 'nobuffer',
                '-flags', 'low_delay',
                '-max_delay', '0',
            ] + logo_input + [
                '-filter_complex',
                '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setpts=PTS-STARTPTS[v0];'
                + ('' if not os.path.exists(logo_file) else f'[1:v]scale=150:-1[logo];[v0][logo]overlay=W-w-15:15[v1];')
                + f'[v1]drawtext=text=\'{text}\':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.7:boxborderw=8:x=(w-text_w)/2:y=h-text_h-15[v]',
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-tune', 'zerolatency',
                '-pix_fmt', 'yuv420p',
                '-b:v', '3000k',
                '-maxrate', '3000k',
                '-bufsize', '6000k',
                '-g', '120',
                '-c:a', 'aac',
                '-b:a', '96k',
                '-ar', '44100',
                '-f', 'flv',
                rtmp_server
            ]
            
            process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            
            while True:
                time.sleep(5)
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    if process.returncode != 0:
                        print_colored(Colors.RED, f"[{name}] ❌ FFmpeg hatası")
                        raise Exception("FFmpeg çöktü")
                    break
            
            print_colored(Colors.YELLOW, f"[{name}] ⏭ Yeniden başlatılıyor...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            print_colored(Colors.RED, f"\n[{name}] ⛔ Durduruluyor...")
            if process:
                process.terminate()
                process.wait()
            break
        except Exception as e:
            retry_count += 1
            print_colored(Colors.RED, f"[{name}] ❌ Hata: {e}")
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            time.sleep(5)

# ===================== ANA FONKSİYON =====================
def main():
    print_colored(Colors.BLUE, "=" * 50)
    print_colored(Colors.GREEN, "  SSH101.com - 3'lü Yayın")
    print_colored(Colors.BLUE, "=" * 50)
    
    if is_termux():
        print_colored(Colors.BLUE, "📱 Termux")
    else:
        print_colored(Colors.BLUE, "💻 Normal ortam")
    
    if not check_dependencies():
        return
    
    # Logo'ları indir
    download_logo(LOGO_URL1, LOGO_FILE1, "ZEM TV")
    download_logo(LOGO_URL2, LOGO_FILE2, "SAD SPOR")
    download_logo(LOGO_URL3, LOGO_FILE3, "GİZLİ BELGESEL")
    
    print_colored(Colors.BLUE, "\n" + "=" * 50)
    print_colored(Colors.GREEN, "✨ 3 Yayın Başlıyor!")
    print_colored(Colors.BLUE, "=" * 50)
    
    # Thread'leri başlat
    threads = []
    
    t1 = threading.Thread(target=start_stream, args=(STREAM_URL1, LOGO_FILE1, RTMP_SERVER1, STREAM_KEY1, TEXT1, "ZEM TV"))
    t1.daemon = True
    t1.start()
    threads.append(t1)
    time.sleep(2)
    
    t2 = threading.Thread(target=start_stream, args=(STREAM_URL2, LOGO_FILE2, RTMP_SERVER2, STREAM_KEY2, TEXT2, "SAD SPOR"))
    t2.daemon = True
    t2.start()
    threads.append(t2)
    time.sleep(2)
    
    t3 = threading.Thread(target=start_stream, args=(STREAM_URL3, LOGO_FILE3, RTMP_SERVER3, STREAM_KEY3, TEXT3, "GİZLİ BELGESEL"))
    t3.daemon = True
    t3.start()
    threads.append(t3)
    
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print_colored(Colors.RED, "\n⛔ Tüm yayınlar durduruluyor...")
        sys.exit(0)

if __name__ == "__main__":
    main()
