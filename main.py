import json
import os
import io
import time
import requests
from google import genai

# Telegram Bot Token ve Chat ID'nizi GitHub Secrets'tan alıyoruz.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini Client Başlatma
client = genai.Client(api_key=GEMINI_API_KEY)

def load_state():
    """Depodaki state.json dosyasını yükler."""
    try:
        with open("state.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"current_index": 0, "topics": []}

def save_state(state):
    """Güncellenmiş state.json dosyasını kaydeder."""
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def update_topics_json(lesson_info, content_data):
    """Üretilen yeni içeriği web sitesinin okuduğu topics.json dosyasına otomatik ekler."""
    try:
        with open("topics.json", "r", encoding="utf-8") as f:
            topics_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        topics_data = {"lgs": {"turkce": {}, "mat": {}, "fen": {}}, "tyt": {"mat": {}}, "yks": {"mat": {}}}

    # state.json içindeki category ve sub bilgilerini alıyoruz
    cat = lesson_info.get('category', 'lgs').lower()
    sub = lesson_info.get('sub', 'mat').lower()

    if cat not in topics_data:
        topics_data[cat] = {}
    if sub not in topics_data[cat]:
        topics_data[cat][sub] = []

    new_id = f"{cat}-{sub}-{int(time.time())}"
    
    # Web sitesi şablonuna uygun bölümleri oluşturuyoruz
    sections = []
    if "ozet" in content_data:
        sections.append({
            "h3": f"Günlük Konu Özeti: {lesson_info['topic']}",
            "p": content_data["ozet"].replace("\n", "<br>")
        })

    questions = []
    if "soru" in content_data:
        questions.append({
            "num": 1,
            "text": content_data["soru"],
            "options": content_data.get("secenekler", []),
            "answer": content_data.get("dogru_cevap_index", 0),
            "solution": content_data.get("cozum", "")
        })

    new_entry = {
        "id": new_id,
        "title": f"📌 {lesson_info['topic']} (Günlük Modül)",
        "tag": f"{cat.upper()} {lesson_info.get('lesson', sub)} • Günlük Akıllı Merkez",
        "heading": lesson_info['topic'],
        "pills": ["✓ Günlük Otomatik İçerik", "✓ Yeni Nesil Soru"],
        "svg": "",
        "sections": sections,
        "trap": "<strong>⚠️ MEB Çeldirici Uyarısı:</strong> Bu konu başlığında soru çözerken kavram yanılgılarına dikkat edin.",
        "questions": questions
    }

    # Yeni içeriği listeye en başa ekliyoruz ki sitede en üstte görünsün
    topics_data[cat][sub].insert(0, new_entry)

    with open("topics.json", "w", encoding="utf-8") as f:
        json.dump(topics_data, f, ensure_ascii=False, indent=2)
    print("topics.json dosyası başarıyla güncellendi ve yeni içerik eklendi!")

def generate_content(lesson_info):
    """Gemini kullanarak o günün konusu için içerik üretir."""
    prompt = f"""
    Sen Türkiye Yüzyılı Maarif Modeli'ne uygun, üst düzey LGS/YKS içerikleri üreten uzman bir eğitmensin.
    Aşağıdaki formatta, sadece geçerli bir JSON çıktısı ver (başka hiçbir metin, açıklama veya markdown kod bloğu ekleme).

    Ders: {lesson_info['lesson']}
    Konu: {lesson_info['topic']}

    Gerekli JSON Yapısı:
    {{
      "gorsel_fikri": "Konunun ana temasını, akış şemasını veya anahtar kavramlarını görselleştiren, DALL-E veya Imagen için detaylı görsel prompt'u (İngilizce). Örn: 'An educational infographic poster illustrating cellular mitosis with clear phases, arrows, and Turkish labels...' ",
      "ozet": "Konuyla ilgili 3 maddelik nokta atışı, akılda kalıcı bilgi özeti (Türkçe)",
      "soru": "Öğrencinin analiz yeteneğini ölçen yeni nesil beceri temelli soru metni (Türkçe)",
      "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "dogru_cevap_index": 0,
      "cozum": "Adım adım mantıksal çözüm ve Maarif Modeli'ne uygun açıklama (Öğrenci yanlış yaptığında açıklama balonunda görünecek metin)"
    }}
    """
    for attempt in range(3):
        try:
            # Model adı yeni SDK standartlarına göre güncellendi
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API Hatası (Deneme {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise e

def generate_infographic_image(visual_idea, lesson_name, topic_name):
    """Gemini Imagen API kullanarak profesyonel infografik görseli üretir."""
    enhanced_prompt = f"""
    An ultra-professional, modern educational infographic poster suitable for high school students.
    The style must be clean, colorful, with clear diagrams, icons, and modern typography.
    The main title at the top must be in Turkish: "{lesson_name.upper()} - {topic_name.upper()}"
    Below the title, illustrate the core concepts and flow as described in the following idea:
    "{visual_idea}"
    Use a cohesive color palette based on the subject.
    Ensure all key textual information points within the diagram are in Turkish.
    The overall look must be premium, clean, and highly informative.
    No watermarks.
    """
    for attempt in range(3):
        try:
            response = client.models.images.generate(
                model='imagen-3.0-generate-001',
                prompt=enhanced_prompt,
                aspect_ratio='9:16'
            )
            image_url = response.generated_images[0].image.url
            return image_url
        except Exception as e:
            print(f"Görsel Üretim Hatası (Deneme {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                return None

def send_telegram_pro_post(data, lesson_info):
    """Üretilen görseli ve akıllı quiz anketini Telegram'da paylaşır."""
    chat_id = TELEGRAM_CHAT_ID
    
    print("Görsel üretiliyor...")
    image_url = generate_infographic_image(data['gorsel_fikri'], lesson_info['lesson'], lesson_info['topic'])
    
    caption_text = f"🚀 **LGS/YKS AKADEMİ | GÜNÜN KONUSU** 🌟\n\n"
    caption_text += f"📌 **{lesson_info['lesson'].upper()}** ➔ _{lesson_info['topic']}_\n\n"
    caption_text += f"👇 Detaylı konu anlatımı ve hemen altındaki akıllı quiz için görseli inceleyin!"

    if image_url:
        try:
            url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload_photo = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": caption_text,
                "parse_mode": "Markdown"
            }
            requests.post(url_photo, data=payload_photo)
        except Exception as e:
            print(f"Görsel gönderilemedi: {e}")
    else:
        url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload_msg = {
            "chat_id": chat_id,
            "text": caption_text,
            "parse_mode": "Markdown"
        }
        requests.post(url_msg, data=payload_msg)

    try:
        url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
        
        poll_data = {
            "chat_id": chat_id,
            "question": f"🧠 [Günün Sorusu] {lesson_info['topic']}",
            "options": json.dumps(data["secenekler"]),
            "type": "quiz",
            "correct_option_id": data["dogru_cevap_index"],
            "is_anonymous": True,
            "explanation": f"💡 Çözüm & İpucu:\n{data['cozum']}",
            "explanation_parse_mode": "Markdown"
        }
        requests.post(url_poll, data=poll_data)
    except Exception as e:
        print(f"Anket gönderilemedi: {e}")

def main():
    print("Bot başlatılıyor...")
    state = load_state()
    current_idx = state["current_index"]
    topics = state["topics"]

    if current_idx >= len(topics):
        print("Tüm konular tamamlandı, başa dönülüyor.")
        current_idx = 0

    lesson_info = topics[current_idx]
    print(f"İçerik üretiliyor: {lesson_info['lesson']} - {lesson_info['topic']}")

    content_data = generate_content(lesson_info)
    
    # 1. Telegram'da paylaş
    send_telegram_pro_post(content_data, lesson_info)
    
    # 2. Web sitesinin topics.json dosyasına otomatik ekle
    update_topics_json(lesson_info, content_data)

    state["current_index"] = current_idx + 1
    save_state(state)
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
