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
    Sen Türkiye Yüzyılı Maarif Modeli'ne uygun LGS içerikleri üreten bir uzmansın.
    Ders: {lesson_info['lesson']}
    Konu: {lesson_info['topic']}
    
    Aşağıdaki JSON formatında çıktı ver (başka hiçbir metin yazma):
    {{
        "ozet": "Konuyla ilgili 3 maddelik net ve kritiği yüksek bilgi özeti metni",
        "soru": "Görsel veya günlük yaşam senaryosuna dayalı yeni nesil beceri temelli soru metni",
        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "dogru_cevap_index": 0,
        "cozum": "Adım adım çözüm ve Maarif Modeli becerisi açıklaması"
    }}
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

def send_telegram_test_post(data, lesson_info):
    caption = f"🧪 **[TEST YAYINI - KİŞİSEL BİLDİRİM]**\n"
    caption += f"📌 **{lesson_info['lesson'].upper()} | {lesson_info['topic']}**\n"
    caption += f"🏷 #{lesson_info['lesson'].replace(' ', '')} #LGS #MaarifModeli\n\n"
    caption += f"💡 **NET ÖZET**\n{data['ozet']}\n\n"
    caption += f"────────────────────────\n\n"
    caption += f"❓ **YENİ NESİL SORU**\n{data['soru']}\n\n"
    caption += f"🔍 **ÇÖZÜM & BECERİ ANALİZİ**\n{data['cozum']}"

    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url_msg, data={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"})

    url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    poll_data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": f"[TEST] {lesson_info['topic']} - Doğru Cevap?",
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
    send_telegram_test_post(content, lesson_info)

    state["current_index"] = current_idx + 1
    save_state(state)

if __name__ == "__main__":
    main()
