import json
import os
import io
import time
import requests
from google import genai
from PIL import Image, ImageDraw, ImageFont

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def load_state():
    with open("state.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def generate_content(lesson_info):
    prompt = f"""
    Sen Türkiye Yüzyılı Maarif Modeli'ne uygun, üst düzey LGS içerikleri üreten uzman bir eğitmensin.
    Ders: {lesson_info['lesson']}
    Konu: {lesson_info['topic']}
    
    Aşağıdaki JSON formatında çıktı ver (başka hiçbir metin yazma):
    {{
        "ozet": "Konuyla ilgili 3 maddelik nokta atışı ve akılda kalıcı bilgi özeti",
        "soru": "Öğrencinin analiz yeteneğini ölçen yeni nesil beceri temelli soru metni",
        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "dogru_cevap_index": 0,
        "cozum": "Adım adım mantıksal çözüm ve Maarif Modeli açıklaması"
    }}
    """
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"API Yoğunluk Hatası (Deneme {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise e

def create_pro_banner(lesson_name, topic_name):
    lesson_lower = lesson_name.lower()
    if "matematik" in lesson_lower:
        bg_color, accent_color = (24, 43, 73), (52, 152, 219)
    elif "fen" in lesson_lower:
        bg_color, accent_color = (20, 90, 50), (46, 204, 113)
    elif "türkçe" in lesson_lower:
        bg_color, accent_color = (120, 40, 31), (231, 76, 60)
    else:
        bg_color, accent_color = (81, 46, 95), (155, 89, 182)

    img = Image.new('RGB', (900, 450), color=bg_color)
    d = ImageDraw.Draw(img)
    
    d.rectangle([0, 0, 900, 35], fill=accent_color)
    d.rectangle([0, 415, 900, 450], fill=accent_color)
    
    try:
        font = ImageFont.load_default()
    except:
        font = None
        
    d.text((60, 120), "LGS MAARİF AKADEMİ", fill=(241, 196, 15), font=font)
    d.text((60, 175), lesson_name.upper(), fill=(255, 255, 255), font=font)
    d.text((60, 235), topic_name, fill=accent_color, font=font)
    
    bio = io.BytesIO()
    bio.name = 'pro_banner.jpg'
    img.save(bio, 'JPEG')
    bio.seek(0)
    return bio

def send_telegram_pro_post(data, lesson_info):
    # 1. Önce Şık Banner Görselini Gönder
    try:
        banner_io = create_pro_banner(lesson_info['lesson'], lesson_info['topic'])
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': ('pro_banner.jpg', banner_io, 'image/jpeg')}
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": f"🎯 {lesson_info['lesson'].upper()} - {lesson_info['topic']}"
        }
        requests.post(url_photo, data=payload, files=files)
    except Exception as e:
        print(f"Görsel gönderilemedi: {e}")

    # 2. Sonra Detaylı Metin Mesajını Gönder (Karakter sınırına takılmaksızın tam iletilir)
    message = f"🚀 LGS MAARİF AKADEMİ | PROFESYONEL ÇALIŞMA 🌟\n\n"
    message += f"📌 {lesson_info['lesson'].upper()} ➔ {lesson_info['topic']}\n\n"
    message += f"💡 Nokta Atışı Özet:\n{data['ozet']}\n\n"
    message += f"────────────────────────\n"
    message += f"❓ Yeni Nesil Soru:\n{data['soru']}\n\n"
    
    message += "📌 Seçenekler:\n"
    for sec in data['secenekler']:
        message += f"{sec}\n"
        
    message += f"\n────────────────────────\n"
    message += f"🔍 Çözüm İpucu:\n{data['cozum']}"

    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url_msg, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    # 3. En Sona İnteraktif Anketi Ekle
    url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    poll_data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": f"🧠 [Günün Sorusu] {lesson_info['topic']}",
        "options": json.dumps(data["secenekler"]),
        "type": "quiz",
        "correct_option_id": data["dogru_cevap_index"],
        "is_anonymous": True
    }
    requests.post(url_poll, data=poll_data)

def main():
    state = load_state()
    current_idx = state["current_index"]
    topics = state["topics"]

    if current_idx >= len(topics):
        current_idx = 0

    lesson_info = topics[current_idx]
    content = generate_content(lesson_info)
    send_telegram_pro_post(content, lesson_info)

    state["current_index"] = current_idx + 1
    save_state(state)

if __name__ == "__main__":
    main()
