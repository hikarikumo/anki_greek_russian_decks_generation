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

# === ЗАГРУЗКА .ENV ===
load_dotenv()

# === НАСТРОЙКИ ===
input_file = "greek_text.txt"  # Файл с предложениями

# anki_deck_name = "Greek decks::AI::101 (Ελληνηκα - Русский)"
# input_words_archive = "input_archive_sentences"
# output_deck = "linq_101.apkg"

anki_deck_name = "Greek decks::AI::ΑΠΟ (Ελληνηκα - Русский)"
input_words_archive = "input_archive_sentences"
output_deck = "ai_apo.apkg"


MODEL_ID = 1607392321
DECK_ID = 2059400121

class GreekSentenceGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        self.model = genanki.Model(
            MODEL_ID,
            'Greek Sentence Model',
            fields=[
                {"name": "Sentence"},
                {"name": "Translation"},
                {"name": "Audio"},
            ],
            templates=[
                {
                    "name": "Greek Sentence -> Russian",
                    "qfmt": '<div class="greek-text">{{Sentence}}</div>',
                    "afmt": """
                        <div class="greek-text">{{Sentence}}</div>
                        <div class="audio-btn">{{Audio}}</div>
                        <hr>
                        <div class="translation">{{Translation}}</div>
                    """,
                }
            ],
            css="""
                .card { font-family: Arial; font-size: 22px; text-align: center; padding: 30px; }
                .greek-text { color: #0045ad; font-size: 32px; font-weight: bold; margin-bottom: 20px; }
                .translation { color: #333; font-style: italic; }
                .audio-btn { margin: 15px 0; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        if not os.path.exists("media_files"): os.makedirs("media_files")

    def get_translation(self, text):
        if not self.client: return "Ошибка API"
        try:
            prompt = (
                f"Translate this Greek sentence to Russian. "
                f"Sentence: '{text}'. "
                "Respond ONLY with JSON: {\"translation\": \"...\"}"
            )
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            return json.loads(response.text).get("translation", "???")
        except Exception as e:
            print(f"⚠️ Ошибка Gemini: {e}")
            return "???"

    def get_tts(self, text):
        if not text: return ""
        # Создаем короткий хеш от текста для уникального имени файла
        txt_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        filename = f"el_sent_{txt_hash}.mp3"
        filepath = os.path.join("media_files", filename)

        if not os.path.exists(filepath):
            try:
                tts = gTTS(text=text, lang='el')
                tts.save(filepath)
            except Exception as e:
                print(f"⚠️ Ошибка TTS: {e}")
                return ""
        
        if filepath not in self.media_files:
            self.media_files.append(filepath)
        return f"[sound:{filename}]"

    def process_line(self, sentence):
        sentence = sentence.strip()
        if not sentence: return
        print(f"🔹 Обработка: {sentence[:50]}...")
        
        translation = self.get_translation(sentence)
        audio = self.get_tts(sentence)

        note = genanki.Note(
            model=self.model,
            fields=[sentence, translation, audio]
        )
        self.deck.add_note(note)
        time.sleep(0.5)

    def create_deck(self, lines):
        for line in lines:
            self.process_line(line)
        
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Готово! Колода: {output_deck}")
        # self.archive_input_file()

    def archive_input_file(self):
        if not os.path.exists(input_words_archive): os.makedirs(input_words_archive)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        with open(input_file, "r", encoding="utf-8") as f: content = f.read()
        with open(f"{input_words_archive}/sent_{timestamp}.txt", "w", encoding="utf-8") as f: f.write(content)
        with open(input_file, "w", encoding="utf-8") as f: f.write("")


# --- Вспомогательные функции ---
def load_lines(filename):
    if not os.path.exists(filename): return []
    with open(filename, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


if __name__ == "__main__":
    gen = GreekSentenceGenerator()
    lines = load_lines(input_file)
    if lines:
        gen.create_deck(lines)
    else:
        print("Файл пуст. Добавьте предложения в greek_text.txt")
