import genanki
import os
import time
import json
import hashlib
from google import genai
from google.genai import types
from datetime import datetime
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

# === НАСТРОЙКИ ===
input_file = "greek_text.txt"  # Файл, куда вставляем греческие предложения

# anki_deck_name = "Greek decks::AI::Recall 101 (Русский - Ελληνηκα)"
# input_words_archive = "input_archive_sentences"
# output_deck = "recall_linq_101.apkg"

anki_deck_name = "Greek decks::AI::Recall ΑΠΟ (Русский - Ελληνηκα)"
input_words_archive = "input_archive_sentences"
output_deck = "recall_ai_apo_mini_michalis.apkg"

# Уникальные ID для модели и колоды
GREEK_MODEL_ID = 1847592034
DECK_ID = 2159400556

class GreekRecallGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        self.model = genanki.Model(
            GREEK_MODEL_ID,
            'Greek Recall Sentence Model',
            fields=[
                {"name": "RussianTranslation"}, # Вопрос
                {"name": "GreekSentence"},      # Ответ
                {"name": "Audio"},              # TTS для греческого
            ],
            templates=[
                {
                    "name": "Recall (Russian -> Greek)",
                    "qfmt": """
                        <div class="card-content">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{RussianTranslation}}</div>
                        </div>
                    """,
                    "afmt": """
                        <div class="card-content">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{RussianTranslation}}</div>
                            <hr>
                            <div class="greek-text">{{GreekSentence}}</div>
                            <div class="audio-btn">{{Audio}}</div>
                        </div>
                    """,
                },
            ],
            css="""
                .card { font-family: Arial; font-size: 20px; text-align: center; color: #333; background-color: #fff; }
                .card-content { padding: 30px; }
                .label { font-size: 14px; color: #888; text-transform: uppercase; margin-bottom: 15px; letter-spacing: 1px; }
                .meaning { font-size: 26px; font-weight: bold; color: #2c3e50; }
                .greek-text { font-size: 34px; font-weight: bold; color: #0045ad; margin: 20px 0; }
                .audio-btn { margin-top: 10px; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        if not os.path.exists("media_files"): os.makedirs("media_files")

    def get_russian_translation(self, greek_text):
        """Получаем перевод предложения на русский через Gemini"""
        if not self.client: return "Ошибка API"
        try:
            prompt = (
                f"Translate this Greek sentence to Russian. "
                f"Sentence: '{greek_text}'. "
                "Respond ONLY with JSON: {\"translation\": \"...\"}"
            )
            response = self.client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            return json.loads(response.text).get("translation", "???")
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            return "???"

    def get_tts(self, text):
        """Генерация аудио для греческого предложения"""
        if not text: return ""
        txt_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        filename = f"el_rec_{txt_hash}.mp3"
        filepath = os.path.join("media_files", filename)

        if not os.path.exists(filepath):
            try:
                tts = gTTS(text=text, lang='el')
                tts.save(filepath)
            except Exception as e:
                print(f"⚠️ TTS error: {e}")
                return ""
        
        if filepath not in self.media_files:
            self.media_files.append(filepath)
        return f"[sound:{filename}]"

    def process_line(self, greek_sentence):
        greek_sentence = greek_sentence.strip()
        if not greek_sentence: return
        
        print(f"🔹 Processing: {greek_sentence[:50]}...")
        
        russian_text = self.get_russian_translation(greek_sentence)
        audio = self.get_tts(greek_sentence)

        note = genanki.Note(
            model=self.model,
            fields=[russian_text, greek_sentence, audio]
        )
        self.deck.add_note(note)
        time.sleep(0.7) # Небольшая задержка для API

    def create_deck(self, lines):
        for line in lines:
            self.process_line(line)
        
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Recall колода создана: {output_deck}")
        self.archive_input_file()

    def archive_input_file(self):
        if not os.path.exists(input_words_archive): os.makedirs(input_words_archive)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        with open(input_file, "r", encoding="utf-8") as f: content = f.read()
        with open(f"{input_words_archive}/recall_sent_{timestamp}.txt", "w", encoding="utf-8") as f: f.write(content)
        with open(input_file, "w", encoding="utf-8") as f: f.write("")

def load_lines(filename):
    if not os.path.exists(filename): return []
    with open(filename, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

if __name__ == "__main__":
    gen = GreekRecallGenerator()
    lines = load_lines(input_file)
    if lines:
        gen.create_deck(lines)
    else:
        print("Файл пуст. Добавьте греческие предложения в greek_text.txt")