import json
import os
import io
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
    Sen Türkiye Yüzyılı Maarif Modeli'ne uygun, öğrenciler için eğlenceli, şıkları tam olan ve akılda kalıcı LGS içerikleri üreten yaratıcı bir uzmansın.
    Ders: {lesson_info['lesson']}
    Konu: {lesson_info['topic']}
    
    Aşağıdaki JSON formatında çıktı ver (başka hiçbir metin yazma):
    {{
        "ozet": "Konuyla ilgili 3 maddelik net, eğlenceli ve akılda kalıcı bilgi özeti metni",
        "soru": "Günlük yaşamdan renkli bir senaryoya dayalı yeni nesil beceri temelli soru metni",
        "secenekler": ["A) Şık 1 metni", "B) Şık 2 metni", "C) Şık 3 metni", "D) Şık 4 metni"],
        "dogru_cevap_index": 2,
        "cozum": "Adım adım çözüm ve Maarif Modeli becerisi açıklaması",
        "gorsel_baslik": "{lesson_info['lesson'].upper()}: {lesson_info['topic']}"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

def create_banner_image(title_text):
    """Python ile şık, renkli ve dikkat çekici bir ders banner görseli üretir"""
    img = Image.new('RGB', (800, 400), color=(41, 128, 185)) # Canlı mavi arka plan
    d = ImageDraw.Draw(img)
    
    # Dekoratif şeritler
    d.rectangle([0, 0, 800, 30], fill=(241, 196, 15)) # Sarı üst şerit
    d.rectangle([0, 370, 800, 400], fill=(46, 204, 113)) # Yeşil alt şerit
    
    # Metin yerleşimi (Sistem fontu varsayılanı)
    try:
        font = ImageFont.load_default()
    except:
        font = None
        
    d.text((50, 150), "LGS MAARİF AKADEMİ", fill=(255, 255, 255), font=font)
    d.text((50, 200), title_text, fill=(255, 243, 128), font=font)
    
    # Belleğe kaydet
    bio = io.BytesIO()
    bio.name = 'banner.jpg'
    img.save(bio, 'JPEG')
    bio.seek(0)
    return bio

def send_telegram_test_post(data, lesson_info):
    # Şık ve eksiksiz metin (Şıklar dahil)
    caption = f"🚀 **LGS MAARİF AKADEMİ | EĞLENCELİ ÖĞRENME** 🌟\n\n"
    caption += f"📌 **{lesson_info['lesson'].upper()}** ➔ _{lesson_info['topic']}_\n"
    caption += f"🏷 #{lesson_info['lesson'].replace(' ', '')} #LGS2026 #MaarifModeli\n\n"
    caption += f"💡 **GÖZ KAMAŞTIRAN ÖZET**\n{data['ozet']}\n\n"
    caption += f"────────────────────────\n\n"
    caption += f"❓ **YENİ NESİL MACERA SORUSU**\n{data['soru']}\n\n"
    
    # Şıkları metne ekleyelim ki çözümle tam uyumlu olsun
    caption += "📌 **SEÇENEKLER:**\n"
    for sec in data['secenekler']:
        caption += f"{sec}\n"
        
    caption += f"\n────────────────────────\n"
    caption += f"🔍 **ADIM ADIM ÇÖZÜM & İPUCU**\n{data['cozum']}"

    # Dinamik görsel üretimi
    banner_io = create_banner_image(lesson_info['topic'])

    # Telegram'a doğrudan üretilen görseli dosya olarak gönder
    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('banner.jpg', banner_io, 'image/jpeg')}
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(url_msg, data=payload, files=files)

    # Etkileşimli Quiz / Anket Gönderimi
    url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    poll_data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": f"🧠 [Günün Sorusu] {lesson_info['topic']} - Doğru Cevap?",
        "options": json.dumps(data["secenekler"]),
        "type": "quiz",
        "correct_option_id": data["dogru_cevap_index"],
        "is_anonymous": True,
        "explanation": f"Doğru Çözüm: {data['cozum'][:150]}..."
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
    send_telegram_test_post(content, lesson_info)

    state["current_index"] = current_idx + 1
    save_state(state)

if __name__ == "__main__":
    main()
