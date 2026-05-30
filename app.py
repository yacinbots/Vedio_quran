from flask import Flask, request, send_file
import requests
import os
import random
import traceback
import subprocess
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

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
# CREATE ARABIC OVERLAY IMAGE (FIXED)
# -----------------------------
def create_overlay(text, footer):
    W, H = 1280, 720

    # إنشاء صورة شفافة
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # تحميل الخط (تأكد من وجود الملف Amiri-Regular.ttf في نفس المجلد)
    # يمكنك تحميله من هنا: https://github.com/aliftype/amiri/releases
    try:
        font_main = ImageFont.truetype("Amiri-Regular.ttf", 54)
        font_footer = ImageFont.truetype("Amiri-Regular.ttf", 32)
    except:
        # إذا لم يكن الخط موجوداً، استخدم الخط الافتراضي
        font_main = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    # إعادة تشكيل النص العربي وعكس اتجاهه بشكل صحيح
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    reshaped_footer = arabic_reshaper.reshape(footer)
    bidi_footer = get_display(reshaped_footer)

    # حساب حجم النص الرئيسي يدوياً (لأن textbbox قد لا يعمل بشكل دقيق مع العربية)
    # نستخدم طريقة textlength و getmask
    try:
        # طريقة أكثر دقة لحساب العرض والارتفاع
        bbox = draw.textbbox((0, 0), bidi_text, font=font_main)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except:
        # طريقة بديلة إذا فشلت textbbox
        tw = font_main.getlength(bidi_text) if hasattr(font_main, 'getlength') else len(bidi_text) * 30
        th = font_main.size if hasattr(font_main, 'size') else 60

    # توسيط النص الرئيسي
    x = (W - tw) // 2
    y = (H - th) // 2

    # رسم النص الرئيسي
    draw.text((x, y), bidi_text, font=font_main, fill=(255, 255, 255, 255))

    # معالجة النص السفلي (التذييل)
    try:
        bbox_footer = draw.textbbox((0, 0), bidi_footer, font=font_footer)
        fw = bbox_footer[2] - bbox_footer[0]
        fh = bbox_footer[3] - bbox_footer[1]
    except:
        fw = font_footer.getlength(bidi_footer) if hasattr(font_footer, 'getlength') else len(bidi_footer) * 20
        fh = font_footer.size if hasattr(font_footer, 'size') else 40

    # رسم التذييل في الأسفل
    footer_x = (W - fw) // 2
    footer_y = H - fh - 30  # 30 بكسل من الأسفل

    draw.text((footer_x, footer_y), bidi_footer, font=font_footer, fill=(255, 255, 255, 255))

    # حفظ الصورة
    img.save("overlay.png")
    print(f"[INFO] Overlay saved: text='{bidi_text}', footer='{bidi_footer}'")

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
        print(f"[INFO] Video URL: {video_url}")

        if not video_url:
            return {"error": "no video"}, 500

        download(video_url, "video.mp4")
        download(info["audio"], "audio.mp3")

        files += ["video.mp4", "audio.mp3"]

        # تحويل الفيديو إلى حجم مناسب
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

        # دمج الفيديو والصوت والنص
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "2",
            "-i", "small.mp4",
            "-i", "audio.mp3",
            "-i", "overlay.png",
            "-filter_complex", "[0:v][2:v]overlay=0:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-c:a", "aac",
            "-shortest",
            "output.mp4"
        ]

        print(f"[INFO] Running FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg stderr: {result.stderr}")
            return {"error": "ffmpeg failed", "details": result.stderr}, 500

        return send_file("output.mp4", as_attachment=True)

    except Exception as e:
        print(traceback.format_exc())
        return {"error": "failed", "message": str(e)}, 500

    finally:
        # تنظيف الملفات المؤقتة
        cleanup_files = ["video.mp4", "audio.mp3", "small.mp4", "overlay.png", "output.mp4"]
        for f in cleanup_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"[INFO] Removed {f}")
                except Exception as e:
                    print(f"[WARN] Could not remove {f}: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
