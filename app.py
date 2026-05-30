from flask import Flask, request, send_file
import requests
import os
import random
import traceback
import subprocess
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"

# -----------------------------
# DOWNLOAD FILE
# -----------------------------
def download(url, path):
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

# -----------------------------
# GET VIDEO (LOW QUALITY)
# -----------------------------
def get_video():
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}

    params = {
        "query": "nature",
        "per_page": 5
    }

    r = requests.get(url, headers=headers, params=params, timeout=20)
    data = r.json()

    videos = data.get("videos", [])
    if not videos:
        return None

    random.shuffle(videos)

    for v in videos:
        files = sorted(v.get("video_files", []), key=lambda x: x.get("width", 9999))
        for f in files:
            if f.get("width", 0) <= 640:
                return f["link"]

    return None

# -----------------------------
# QURAN AYAH
# -----------------------------
def get_ayah(surah, ayah):
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.alafasy"
    r = requests.get(url, timeout=20)
    data = r.json()["data"]

    return {
        "text": data["text"],
        "audio": data["audio"],
        "surah": data["surah"]["name"],
        "ayah": data["numberInSurah"]
    }

# -----------------------------
# FUNCTION TO REVERSE ARABIC TEXT CORRECTLY
# -----------------------------
def reverse_arabic_text(text):
    """
    تقوم بعكس النص العربي مع الحفاظ على شكل الحروف
    """
    # نقسم النص إلى كلمات
    words = text.split()
    # نعكس ترتيب الكلمات
    reversed_words = words[::-1]
    # نعيد تجميع النص
    return ' '.join(reversed_words)

# -----------------------------
# CREATE OVERLAY WITH CORRECT ARABIC
# -----------------------------
def create_overlay(text, footer):
    W, H = 1280, 720

    # إنشاء صورة شفافة
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # تحميل الخط
    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 54)
    except:
        try:
            font_main = ImageFont.truetype("arial.ttf", 54)
        except:
            font_main = ImageFont.load_default()
    
    try:
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 32)
    except:
        try:
            font_footer = ImageFont.truetype("arial.ttf", 32)
        except:
            font_footer = ImageFont.load_default()

    # IMPORTANT: عكس النص العربي يدوياً
    # النص الأصلي: "بسم الله الرحمن الرحيم"
    # بعد العكس: "الرحيم الرحمن الله بسم"
    reversed_text = reverse_arabic_text(text)
    reversed_footer = reverse_arabic_text(footer)
    
    print(f"[DEBUG] Original text: {text}")
    print(f"[DEBUG] Reversed text: {reversed_text}")

    # رسم خلفية سوداء شفافة للنص ليسهل رؤيته
    # حساب حجم النص
    try:
        bbox = draw.textbbox((0, 0), reversed_text, font=font_main)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except:
        tw = len(reversed_text) * 30
        th = 60

    # توسيط النص
    x = (W - tw) // 2
    y = (H - th) // 2

    # رسم ظل للنص ليكون أوضح
    # ظل أسود
    draw.text((x-2, y-2), reversed_text, font=font_main, fill=(0, 0, 0, 255))
    draw.text((x+2, y-2), reversed_text, font=font_main, fill=(0, 0, 0, 255))
    draw.text((x-2, y+2), reversed_text, font=font_main, fill=(0, 0, 0, 255))
    draw.text((x+2, y+2), reversed_text, font=font_main, fill=(0, 0, 0, 255))
    
    # النص الأساسي باللون الأبيض
    draw.text((x, y), reversed_text, font=font_main, fill=(255, 255, 255, 255))

    # رسم التذييل
    try:
        bbox_f = draw.textbbox((0, 0), reversed_footer, font=font_footer)
        fw = bbox_f[2] - bbox_f[0]
        fh = bbox_f[3] - bbox_f[1]
    except:
        fw = len(reversed_footer) * 20
        fh = 40

    footer_x = (W - fw) // 2
    footer_y = H - fh - 40

    # ظل للتذييل
    draw.text((footer_x-2, footer_y-2), reversed_footer, font=font_footer, fill=(0, 0, 0, 255))
    draw.text((footer_x+2, footer_y-2), reversed_footer, font=font_footer, fill=(0, 0, 0, 255))
    draw.text((footer_x-2, footer_y+2), reversed_footer, font=font_footer, fill=(0, 0, 0, 255))
    draw.text((footer_x+2, footer_y+2), reversed_footer, font=font_footer, fill=(0, 0, 0, 255))
    
    # التذييل الأساسي
    draw.text((footer_x, footer_y), reversed_footer, font=font_footer, fill=(255, 255, 255, 255))

    # حفظ الصورة
    img.save("overlay.png")
    print(f"[INFO] Overlay saved successfully")

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return "Quran Video API Running"

# -----------------------------
# GENERATE VIDEO
# -----------------------------
@app.route("/generate", methods=["GET"])
def generate():
    files = []

    try:
        surah = request.args.get("surah", "1")
        ayah = request.args.get("ayah", "1")

        print(f"[INFO] Generating for Surah {surah}, Ayah {ayah}")
        
        info = get_ayah(surah, ayah)
        print(f"[INFO] Ayah text: {info['text']}")
        
        video_url = get_video()

        if not video_url:
            return {"error": "no video"}, 500

        download(video_url, "video.mp4")
        download(info["audio"], "audio.mp3")

        files += ["video.mp4", "audio.mp3"]

        # معالجة الفيديو
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "video.mp4",
            "-t", "25",
            "-vf", "scale=1280:720",
            "small.mp4"
        ], capture_output=True, text=True)

        files.append("small.mp4")

        footer = f"{info['surah']} | آية {info['ayah']}"
        create_overlay(info["text"], footer)

        files.append("overlay.png")

        # دمج كل شيء
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "2",
            "-i", "small.mp4",
            "-i", "audio.mp3",
            "-i", "overlay.png",
            "-filter_complex", "[0:v][2:v]overlay=0:0:format=auto,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-c:a", "aac",
            "-shortest",
            "-pix_fmt", "yuv420p",
            "output.mp4"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg error: {result.stderr}")
            return {"error": "ffmpeg failed"}, 500

        return send_file("output.mp4", as_attachment=True)

    except Exception as e:
        print(traceback.format_exc())
        return {"error": "failed", "message": str(e)}, 500

    finally:
        # تنظيف الملفات
        for f in ["video.mp4", "audio.mp3", "small.mp4", "overlay.png", "output.mp4"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
