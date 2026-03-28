import genanki
import os
import time
import json
from google import genai
from google.genai import types
from datetime import datetime
from gtts import gTTS
from dotenv import load_dotenv

# === ЗАГРУЗКА .ENV ===
load_dotenv()

# === НАСТРОЙКИ ===
input_file = "greek_words.txt"
anki_deck_name = "Greek decks::Ελληνικά::Reading Practice (Trans)"
output_deck = "greek_reading_trans.apkg"
input_words_archive = "input_words_archive/reading_practice"

# Уникальные ID для этой модели
READING_MODEL_ID = 1607392322
DECK_ID = 2059400122

class GreekReadingGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("❌ ОШИБКА: GOOGLE_API_KEY не найден.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        # Модель: Слово -> Перевод + Аудио
        self.model = genanki.Model(
            READING_MODEL_ID,
            'Greek Reading with Translation',
            fields=[
                {"name": "Word"},
                {"name": "Translation"},
                {"name": "Audio"},
            ],
            templates=[
                {
                    "name": "Reading & Translation",
                    "qfmt": '<div class="greek-word">{{Word}}</div>',
                    "afmt": """
                        <div class="greek-word">{{Word}}</div>
                        <div class="audio-control">{{Audio}}</div>
                        <hr id="answer">
                        <div class="translation">{{Translation}}</div>
                    """,
                }
            ],
            css="""
                .card { font-family: Arial; font-size: 24px; text-align: center; color: black; background-color: white; padding: 20px; }
                .greek-word { font-size: 50px; font-weight: bold; color: #0045ad; margin-bottom: 10px; }
                .translation { font-size: 30px; color: #555; font-style: italic; margin-top: 20px; }
                .audio-control { margin-top: 10px; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        
        if not os.path.exists("media_files"):
            os.makedirs("media_files")

    def get_translation(self, word):
        """Получаем только перевод через Gemini"""
        if not self.client: return "???"
        try:
            prompt = f"Translate the Greek word or phrase '{word}' into Russian. Respond ONLY with the Russian translation, no extra text."
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return response.text.strip() if response.text else "???"
        except Exception as e:
            print(f"⚠️ Ошибка Gemini для '{word}': {e}")
            return "???"

    def get_tts_audio(self, text):
        """Генерация озвучки через gTTS"""
        if not text: return ""
        safe_text = "".join([c for c in text if c.isalnum()])[:20]
        filename = f"read_{safe_text}_{int(time.time())}.mp3"
        filepath = os.path.join("media_files", filename)

        try:
            tts = gTTS(text=text, lang='el')
            tts.save(filepath)
            self.media_files.append(filepath)
            return f"[sound:{filename}]"
        except Exception as e:
            print(f"⚠️ Ошибка TTS для '{text}': {e}")
            return ""

    def process_word(self, word):
        print(f"🔹 Обработка: {word}")
        translation = self.get_translation(word)
        audio = self.get_tts_audio(word)

        note = genanki.Note(
            model=self.model,
            fields=[word, translation, audio]
        )
        self.deck.add_note(note)
        time.sleep(0.5) # Небольшая пауза для API

    def create_deck(self, words):
        for w in words:
            self.process_word(w)
        
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Колода создана: {output_deck}")
        self.archive_input_file()

    def archive_input_file(self):
        if not os.path.exists(input_words_archive): os.makedirs(input_words_archive)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        if os.path.exists(input_file):
            with open(input_file, "r", encoding="utf-8") as f: content = f.read()
            if content.strip():
                with open(f"{input_words_archive}/reading_{timestamp}.txt", "w", encoding="utf-8") as f: f.write(content)
                with open(input_file, "w", encoding="utf-8") as f: f.write("")

def get_words_from_file(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

if __name__ == "__main__":
    words = get_words_from_file(input_file)
    if words:
        gen = GreekReadingGenerator()
        gen.create_deck(words)
    else:
        print("Нет новых слов в файле.")