import json
import os
import requests
from google import genai

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
    Sen Türkiye Yüzyılı Maarif Modeli'ne uygun, öğrenciler için eğlenceli ve akılda kalıcı LGS içerikleri üreten yaratıcı bir uzmansın.
    Ders: {lesson_info['lesson']}
    Konu: {lesson_info['topic']}
    
    Aşağıdaki JSON formatında çıktı ver (başka hiçbir metin yazma):
    {{
        "ozet": "Konuyla ilgili 3 maddelik net, eğlenceli ve akılda kalıcı bilgi özeti metni",
        "soru": "Günlük yaşamdan renkli bir senaryoya dayalı yeni nesil beceri temelli soru metni",
        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "dogru_cevap_index": 0,
        "cozum": "Adım adım çözüm ve Maarif Modeli becerisi açıklaması",
        "gorsel_aciklamasi": "Bu soru ve konu için çocukların ilgisini çekecek, renkli çizgi film tarzı bir illüstrasyon veya eğlenceli bir sahne açıklaması (örneğin: 'Renkli sebzelerle dolu neşeli bir dikey tarım çiftliği, neon mavi ve kırmızı LED ışıklar altında sevimli robotlar')"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

def send_telegram_test_post(data, lesson_info):
    # Çocukların dikkatini çekecek eğlenceli emoji ve başlıklar
    caption = f"🚀 **LGS MAARİF AKADEMİ | EĞLENCELİ ÖĞRENME** 🌟\n\n"
    caption += f"📌 **{lesson_info['lesson'].upper()}** ➔ _{lesson_info['topic']}_\n"
    caption += f"🎨 *Görsel Konsept:* `{data.get('gorsel_aciklamasi', 'Eğlenceli ders konsepti')}`\n"
    caption += f"🏷 #{lesson_info['lesson'].replace(' ', '')} #LGS2026 #MaarifModeli\n\n"
    caption += f"💡 **GÖZ KAMAŞTIRAN ÖZET**\n{data['ozet']}\n\n"
    caption += f"────────────────────────\n\n"
    caption += f"❓ **YENİ NESİL MACERA SORUSU**\n{data['soru']}\n\n"
    caption += f"🔍 **ADIM ADIM ÇÖZÜM & İPUCU**\n{data['cozum']}"

    # İlgi çekici, derslere özel renkli ve güvenilir bir banner/illüstrasyon görseli (Unsplash üzerinden dinamik görsel)
    # İlerleyen aşamalarda kendi özel görsellerinizle de değiştirebilirsiniz.
    banner_url = "https://images.unsplash.com/photo-1509062522246-3755977927d7?q=80&w=1000&auto=format&fit=crop"

    # Fotoğraflı Mesaj Gönderimi (sendPhoto)
    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": banner_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(url_msg, data=payload)

    # Etkileşimli Quiz / Anket Gönderimi
    url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    poll_data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": f"🧠 [Günün Sorusu] {lesson_info['topic']} - Doğru Cevap?",
        "options": json.dumps(data["secenekler"]),
        "type": "quiz",
        "correct_option_id": data["dogru_cevap_index"],
        "is_anonymous": True,
        "explanation": "Tebrikler! Açıklamayı okuyarak konuyu pekiştirdin."
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
