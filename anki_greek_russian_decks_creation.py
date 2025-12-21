import genanki
import requests
import os
import time
import json
import urllib.parse
from google import genai  # Новый импорт
from google.genai import types # Типы для конфига
from datetime import datetime
from gtts import gTTS
from dotenv import load_dotenv

# Загрузка переменных окружения (если используете .env файл)
load_dotenv()

# === НАСТРОЙКИ ФАЙЛОВ ===
input_file = "greek_words.txt"
anki_deck_name = "greekpod101_simple_dialogues"
output_deck = "greekpod101_simple_dialogues.apkg"
input_words_archive = "input_words_archive_greekpod101_simple_dialogues"

# === НАСТРОЙКИ МОДЕЛИ ANKI ===
GREEK_MODEL_ID = 1607392320
DECK_ID = 2059400120

class GreekAnkiGenerator:
    def __init__(self):
        # 1. Инициализация НОВОГО клиента Google GenAI
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("❌ ОШИБКА: GOOGLE_API_KEY не найден в переменных окружения.")
            self.client = None
        else:
            # Новый способ инициализации через Client
            self.client = genai.Client(api_key=self.api_key)

        # Модель карточки (без изменений)
        self.model = genanki.Model(
            GREEK_MODEL_ID,
            anki_deck_name,
            fields=[
                {"name": "GreekWord"},      
                {"name": "Translation"},    
                {"name": "WordAudio"},      
                {"name": "Example"},        
                {"name": "ExampleTrans"},   
                {"name": "ExampleAudio"},   
            ],
            templates=[
                {
                    "name": "Greek -> Russian",
                    "qfmt": """
                        <div class="greek-word">{{GreekWord}}</div>
                        <div class="audio-btn">{{WordAudio}}</div>
                    """,
                    "afmt": """
                        <div class="greek-word">{{GreekWord}}</div>
                        <div class="audio-btn">{{WordAudio}}</div>
                        <hr>
                        <div class="meaning">{{Translation}}</div>
                        <div class="example-box">
                            <div class="example">{{Example}} {{ExampleAudio}}</div>
                            <div class="example-meaning">{{ExampleTrans}}</div>
                        </div>
                    """,
                },
                {
                    "name": "Russian -> Greek",
                    "qfmt": """
                        <div class="meaning">{{Translation}}</div>
                    """,
                    "afmt": """
                        <div class="meaning">{{Translation}}</div>
                        <hr>
                        <div class="greek-word">{{GreekWord}}</div>
                        <div class="audio-btn">{{WordAudio}}</div>
                        <div class="example-box">
                            <div class="example">{{Example}} {{ExampleAudio}}</div>
                            <div class="example-meaning">{{ExampleTrans}}</div>
                        </div>
                    """,
                },
            ],
            css="""
                .card { font-family: Arial, sans-serif; font-size: 20px; text-align: center; color: black; background-color: white; padding: 20px; }
                .greek-word { font-family: "Helvetica", sans-serif; font-size: 40px; font-weight: bold; color: #0045ad; margin-bottom: 10px; }
                .meaning { font-size: 24px; margin-bottom: 20px; font-weight: bold; color: #333; }
                .example-box { margin-top: 20px; padding: 15px; background-color: #f0f7ff; border-radius: 8px; border-left: 5px solid #0045ad; text-align: left; }
                .example { font-size: 20px; margin-bottom: 5px; color: #000; }
                .example-meaning { font-size: 16px; font-style: italic; color: #555; }
                .audio-btn { margin: 10px 0; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        
        if not os.path.exists("media_files"):
            os.makedirs("media_files")

    def get_gemini_data(self, word):
        """Получает перевод и пример через Gemini (Новый API)"""
        if not self.client:
            return None

        try:
            prompt = (
                f"You are a Greek language teacher. I give you the word: '{word}'. "
                "1. Translate it to Russian. "
                "2. Create one simple, natural Greek example sentence using this word. "
                "3. Translate that example to Russian. "
                "Respond ONLY in JSON format: "
                "{\"translation\": \"...\", \"example_greek\": \"...\", \"example_russian\": \"...\"}"
            )

            # 2. Обновленный вызов API
            response = self.client.models.generate_content(
                model='gemini-2.0-flash', # Можно использовать gemini-1.5-flash или gemini-2.0-flash
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
            # В новом SDK response.text работает так же
            if response.text:
                return json.loads(response.text)
                
        except Exception as e:
            print(f"⚠️ Ошибка Gemini API для '{word}': {e}")
        
        return None

    def get_forvo_audio(self, word):
        """Качает произношение слова с Forvo"""
        save_path = f"media_files/el_{word}.mp3"
        if os.path.exists(save_path):
            self.media_files.append(save_path)
            return f"[sound:el_{word}.mp3]"

        key = os.getenv("FORVO_API_KEY")
        if not key:
            # print("⚠️ Нет FORVO_API_KEY") 
            return ""

        encoded_word = urllib.parse.quote(word)
        url = f"https://apifree.forvo.com/key/{key}/format/json/action/word-pronunciations/word/{encoded_word}/language/el"

        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if "items" in data and len(data["items"]) > 0:
                mp3_url = data["items"][0]["pathmp3"]
                doc = requests.get(mp3_url)
                with open(save_path, 'wb') as f:
                    f.write(doc.content)
                self.media_files.append(save_path)
                print(f"   🔊 Audio (Forvo) скачано")
                return f"[sound:el_{word}.mp3]"
        except Exception as e:
            print(f"⚠️ Ошибка Forvo: {e}")
        
        return ""

    def get_tts_audio(self, text, file_prefix):
        """Генерирует TTS для предложения"""
        if not text: return ""
        
        safe_name = "".join([c for c in file_prefix if c.isalpha() or c.isdigit()])[:20]
        filename = f"tts_{safe_name}_{int(time.time())}.mp3"
        filepath = f"media_files/{filename}"

        try:
            tts = gTTS(text=text, lang='el')
            tts.save(filepath)
            self.media_files.append(filepath)
            return f"[sound:{filename}]"
        except Exception as e:
            print(f"⚠️ Ошибка TTS: {e}")
            return ""

    def process_word(self, word):
        print(f"\n🔹 Обработка: {word}")
        
        ai_data = self.get_gemini_data(word)
        
        translation = ""
        example_el = ""
        example_ru = ""
        
        if ai_data:
            translation = ai_data.get("translation", "")
            example_el = ai_data.get("example_greek", "")
            example_ru = ai_data.get("example_russian", "")
            print(f"   📖 Перевод: {translation}")
        else:
            print("   ⚠️ Не удалось получить данные от Gemini")

        word_audio = self.get_forvo_audio(word)

        ex_audio = ""
        if example_el:
            ex_audio = self.get_tts_audio(example_el, word)

        note = genanki.Note(
            model=self.model,
            fields=[
                word,
                translation,
                word_audio,
                example_el,
                example_ru,
                ex_audio
            ]
        )
        self.deck.add_note(note)
        time.sleep(1) 
        
        return {"word": word, "trans": translation}

    def create_deck(self, words):
        results = []
        for w in words:
            res = self.process_word(w)
            results.append(res)
        
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Колода создана: {output_deck}")
        
        self.archive_input_file()

    def archive_input_file(self):
        if not os.path.exists(input_words_archive):
            os.makedirs(input_words_archive)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        archive_name = f"greek_words_{timestamp}.txt"
        
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        with open(f"{input_words_archive}/{archive_name}", "w", encoding="utf-8") as f:
            f.write(content)
            
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("")
            
        print(f"📂 Файл перемещен в архив: {archive_name}")

def check_input_duplicates(filename):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f: pass
        return []

    archived_words = set()
    if os.path.exists(input_words_archive):
        for f_name in os.listdir(input_words_archive):
            with open(os.path.join(input_words_archive, f_name), "r", encoding="utf-8") as f:
                for line in f:
                    archived_words.add(line.strip())

    new_words = []
    with open(filename, "r", encoding="utf-8") as f:
        candidates = [line.strip() for line in f if line.strip()]

    unique_candidates = list(set(candidates))
    
    for w in unique_candidates:
        if w in archived_words:
            print(f"♻️ Дубликат (уже был в архиве): {w}")
        else:
            new_words.append(w)
    
    with open(filename, "w", encoding="utf-8") as f:
        for w in new_words:
            f.write(w + "\n")
            
    return new_words

if __name__ == "__main__":
    generator = GreekAnkiGenerator()
    
    words_to_process = check_input_duplicates(input_file)
    
    if words_to_process:
        print(f"Найдено новых слов: {len(words_to_process)}")
        generator.create_deck(words_to_process)
    else:
        print(f"Нет новых слов для обработки в {input_file}")