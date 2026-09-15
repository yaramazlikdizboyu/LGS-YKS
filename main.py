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
        # İlk çalıştırma için varsayılan yapı
        return {"current_index": 0, "topics": []}

def save_state(state):
    """Güncellenmiş state.json dosyasını kaydeder."""
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

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
            response = client.models.generate_content(
                model='gemini-1.5-flash', # Hızlı ve güncel model
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
    # Görselin üzerine Türkçe başlıkları ve dersi eklemek için detaylı prompt
    enhanced_prompt = f"""
    An ultra-professional, modern educational infographic poster suitable for high school students.
    The style must be clean, colorful, with clear diagrams, icons, and modern typography.
    The main title at the top must be in Turkish: "{lesson_name.upper()} - {topic_name.upper()}"
    Below the title, illustrate the core concepts and flow as described in the following idea:
    "{visual_idea}"
    Use a cohesive color palette based on the subject (e.g., Blue for Math, Green for Science).
    Ensure all key textual information points within the diagram are in Turkish.
    The overall look must be premium, clean, and highly informative.
    No watermarks.
    """
    for attempt in range(3):
        try:
            response = client.models.images.generate(
                model='imagen-3.0-generate-001',
                prompt=enhanced_prompt,
                aspect_ratio='9:16' # Dikey poster formatı
            )
            # Üretilen görselin URL'sini alıyoruz
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
    
    # 1. ADIM: Profesyonel İnfografik Görseli Üret ve Gönder
    print("Görsel üretiliyor...")
    image_url = generate_infographic_image(data['gorsel_fikri'], lesson_info['lesson'], lesson_info['topic'])
    
    # Görselin hemen altındaki metin başlığı
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
        print("Görsel oluşturulamadı, sadece metin gönderiliyor.")
        # Görsel yoksa bile metni gönder
        url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload_msg = {
            "chat_id": chat_id,
            "text": caption_text,
            "parse_mode": "Markdown"
        }
        requests.post(url_msg, data=payload_msg)

    # 2. ADIM: Hemen Arkasından Akıllı Quiz Anketi Gönder
    # Bu anket tıklandığında anında renklenir ve yanlışta açıklama balonu çıkarır.
    try:
        url_poll = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
        
        poll_data = {
            "chat_id": chat_id,
            "question": f"🧠 [Günün Sorusu] {lesson_info['topic']}",
            "options": json.dumps(data["secenekler"]),
            "type": "quiz",
            "correct_option_id": data["dogru_cevap_index"],
            "is_anonymous": True, # Oylamanın anonim olması önerilir
            # ÖĞRENCİ YANLIŞ YAPTIĞINDA ÇIKACAK GEREKÇELİ AÇIKLAMA:
            "explanation": f"💡 Çözüm & İpucu:\n{data['cozum']}",
            "explanation_parse_mode": "Markdown"
        }
        requests.post(url_poll, data=poll_data)
    except Exception as e:
        print(f"Anket gönderilemedi: {e}")

def main():
    """Ana yürütücü fonksiyon."""
    print("Bot başlatılıyor...")
    state = load_state()
    current_idx = state["current_index"]
    topics = state["topics"]

    # Eğer tüm konular bittiyse başa dön
    if current_idx >= len(topics):
        print("Tüm konular tamamlandı, başa dönülüyor.")
        current_idx = 0

    # Sıradaki ders ve konu bilgisini al
    lesson_info = topics[current_idx]
    print(f"İçerik üretiliyor: {lesson_info['lesson']} - {lesson_info['topic']}")

    # Gemini'den içeriği ve görsel fikrini iste
    content_data = generate_content(lesson_info)

    # Telegram'da profesyonel gönderiyi oluştur (Görsel + Akıllı Quiz)
    send_telegram_pro_post(content_data, lesson_info)

    # State'i güncelle (Bir sonraki konuya geçmek için)
    state["current_index"] = current_idx + 1
    save_state(state)
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
