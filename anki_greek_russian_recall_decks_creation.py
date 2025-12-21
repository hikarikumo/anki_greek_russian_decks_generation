import genanki
import requests
import os
import time
import json
import urllib.parse
from google import genai
from google.genai import types
from datetime import datetime
from gtts import gTTS
from dotenv import load_dotenv

# === ЗАГРУЗКА .ENV (API КЛЮЧИ) ===
load_dotenv()

# === НАСТРОЙКИ ФАЙЛОВ ===
input_file = "greek_words.txt"

# Название колоды и файла
input_file = "greek_words.txt"
anki_deck_name = "greekpod101_simple_dialogues_recall"
output_deck = "greekpod101_simple_dialogues_recall.apkg"
input_words_archive = "input_words_archive_greekpod101_simple_dialogues_recall"

# Уникальные ID (сгенерированы случайно, чтобы не конфликтовать с китайскими)
GREEK_MODEL_ID = 1847592033
DECK_ID = 2159400555

class GreekAnkiGenerator:
    def __init__(self):
        # 1. Инициализация клиента Google GenAI (New SDK)
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("❌ ОШИБКА: GOOGLE_API_KEY не найден. Проверьте .env или переменные среды.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        # 2. Модель карточки (RECALL LOGIC)
        self.model = genanki.Model(
            GREEK_MODEL_ID,
            anki_deck_name,
            fields=[
                {"name": "GreekWord"},      # Ответ (Скрыто)
                {"name": "Translation"},    # Вопрос (Лицевая сторона)
                {"name": "WordAudio"},      # Аудио слова
                {"name": "Example"},        # Пример (Греческий)
                {"name": "ExampleTrans"},   # Перевод примера
                {"name": "ExampleAudio"},   # Озвучка примера
            ],
            templates=[
                {
                    # RECALL: Russian -> Greek
                    "name": "Recall (Russian -> Greek)",
                    "qfmt": """
                        <div class="card-content">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{Translation}}</div>
                        </div>
                    """,
                    "afmt": """
                        <div class="card-content">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{Translation}}</div>
                            <hr>
                            <div class="greek-word">{{GreekWord}}</div>
                            <div class="audio-btn">{{WordAudio}}</div>
                            
                            <div class="example-box">
                                <div class="example-greek">{{Example}} {{ExampleAudio}}</div>
                                <div class="example-trans">{{ExampleTrans}}</div>
                            </div>
                        </div>
                    """,
                },
            ],
            css="""
                .card { font-family: Arial, sans-serif; font-size: 20px; text-align: center; color: #333; background-color: #ffffff; }
                .card-content { padding: 20px; }
                
                /* Стили для вопроса (Русский) */
                .label { font-size: 14px; color: #888; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
                .meaning { font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; }

                /* Стили для ответа (Греческий) */
                .greek-word { font-family: "Helvetica", sans-serif; font-size: 42px; font-weight: bold; color: #0045ad; margin: 15px 0; }
                
                /* Стили для примеров */
                .example-box { 
                    margin-top: 25px; 
                    padding: 15px; 
                    background-color: #f4f9ff; 
                    border-radius: 8px; 
                    border-left: 5px solid #0045ad; 
                    text-align: left; 
                }
                .example-greek { font-size: 20px; color: #000; margin-bottom: 6px; line-height: 1.4; }
                .example-trans { font-size: 16px; color: #666; font-style: italic; }
                
                .audio-btn { margin-top: 10px; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = [] # Список файлов для упаковки в apkg
        
        # Создаем папку для медиа, если нет
        if not os.path.exists("media_files"):
            os.makedirs("media_files")

    def get_gemini_data(self, word):
        """
        Запрашивает перевод и пример у Gemini.
        Возвращает JSON.
        """
        if not self.client:
            return None

        try:
            # Промпт настроен на создание JSON
            prompt = (
                f"You are a professional Greek tutor. Target word: '{word}'.\n"
                "1. Provide the Russian translation (meaning).\n"
                "2. Create a simple, natural Greek example sentence using this word.\n"
                "3. Provide the Russian translation of that example.\n"
                "Respond ONLY with a valid JSON object using these keys: "
                "{\"translation\": \"...\", \"example_greek\": \"...\", \"example_russian\": \"...\"}"
            )

            response = self.client.models.generate_content(
                model='gemini-2.0-flash', # Быстрая и дешевая модель
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )

            if response.text:
                return json.loads(response.text)
        
        except Exception as e:
            print(f"⚠️ Ошибка Gemini API для '{word}': {e}")
            return None

    def get_forvo_audio(self, word):
        """Скачивает произношение слова с Forvo (как в китайском скрипте)"""
        audio_dir = "media_files"
        filename = f"el_{word}.mp3"
        filepath = os.path.join(audio_dir, filename)

        # Если файл уже есть, не качаем снова
        if os.path.exists(filepath):
            self.media_files.append(filepath)
            return f"[sound:{filename}]"

        key = os.getenv("FORVO_API_KEY")
        if not key:
            return ""

        encoded_word = urllib.parse.quote(word)
        url = f"https://apifree.forvo.com/key/{key}/format/json/action/word-pronunciations/word/{encoded_word}/language/el"

        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if "items" in data and len(data["items"]) > 0:
                # Сортируем по рейтингу (как в твоем скрипте)
                items = sorted(data["items"], key=lambda x: int(x.get("num_positive_votes", 0)), reverse=True)
                mp3_url = items[0]["pathmp3"]
                
                doc = requests.get(mp3_url)
                with open(filepath, 'wb') as f:
                    f.write(doc.content)
                
                self.media_files.append(filepath)
                print(f"   🔊 Forvo: скачано аудио для {word}")
                return f"[sound:{filename}]"
        except Exception as e:
            print(f"⚠️ Ошибка Forvo: {e}")
        
        return ""

    def get_tts_audio(self, text, prefix):
        """Генерирует озвучку предложения через Google TTS"""
        if not text: return ""
        
        # Очистка имени файла
        safe_prefix = "".join([c for c in prefix if c.isalnum()])[:15]
        timestamp = int(time.time())
        filename = f"tts_{safe_prefix}_{timestamp}.mp3"
        filepath = os.path.join("media_files", filename)

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
        
        # 1. Запрос к AI
        ai_data = self.get_gemini_data(word)
        
        translation = "???"
        example_el = ""
        example_ru = ""

        if ai_data:
            translation = ai_data.get("translation", "???")
            example_el = ai_data.get("example_greek", "")
            example_ru = ai_data.get("example_russian", "")
            print(f"   📖 Перевод: {translation}")
        
        # 2. Аудио
        word_audio = self.get_forvo_audio(word)
        
        # 3. Аудио примера (TTS)
        ex_audio = ""
        if example_el:
            ex_audio = self.get_tts_audio(example_el, word)

        # 4. Создание заметки
        note = genanki.Note(
            model=self.model,
            fields=[
                word,           # GreekWord
                translation,    # Translation (Front)
                word_audio,     # WordAudio
                example_el,     # Example
                example_ru,     # ExampleTrans
                ex_audio        # ExampleAudio
            ]
        )
        self.deck.add_note(note)
        time.sleep(1) # Вежливость к API

        return {"word": word, "trans": translation}

    def create_deck(self, words):
        results = []
        for w in words:
            res = self.process_word(w)
            results.append(res)
        
        # Экспорт
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Колода создана: {output_deck}")
        
        # Архивация (как в исходном скрипте)
        self.archive_input_file()

    def archive_input_file(self):
        if not os.path.exists(input_words_archive):
            os.makedirs(input_words_archive)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        archive_name = f"greek_words_{timestamp}.txt"
        
        # Читаем исходный
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Пишем в архив
        with open(f"{input_words_archive}/{archive_name}", "w", encoding="utf-8") as f:
            f.write(content)
            
        # Очищаем исходный
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("")
            
        print(f"📂 Файл {input_file} перемещен в архив: {archive_name}")


def check_input_duplicates(filename):
    """
    Проверяет дубликаты, сравнивая input_file со всеми файлами в архиве.
    Полная копия логики из китайского скрипта.
    """
    if not os.path.exists(filename):
        # Создаем пустой файл, если нет
        with open(filename, "w", encoding="utf-8") as f: 
            f.write("καλημέρα\n") # Пример слова
        print(f"Created example file: {filename}")
        return ["καλημέρα"]

    # 1. Собираем все слова из архива
    archived_words = set()
    if os.path.exists(input_words_archive):
        files = os.listdir(input_words_archive)
        for f_name in files:
            full_path = os.path.join(input_words_archive, f_name)
            with open(full_path, "r", encoding="utf-8") as f:
                for line in f:
                    clean_line = line.strip()
                    if clean_line:
                        archived_words.add(clean_line)

    # 2. Читаем новые слова
    new_input_words = []
    with open(filename, "r", encoding="utf-8") as f:
        current_words = [line.strip() for line in f if line.strip()]

    # Удаляем дубли внутри самого файла
    unique_current = list(set(current_words))
    
    # 3. Фильтруем
    final_list = []
    for w in unique_current:
        if w in archived_words:
            print(f"♻️ Дубликат (уже был в архиве): {w}")
        else:
            final_list.append(w)
    
    print(f"Найдено слов в архиве: {len(archived_words)}")
    print(f"К обработке: {len(final_list)}")
    
    # Перезаписываем input файл только чистыми словами (опционально, но полезно)
    with open(filename, "w", encoding="utf-8") as f:
        for w in final_list:
            f.write(w + "\n")
            
    return final_list

if __name__ == "__main__":
    generator = GreekAnkiGenerator()
    
    # 1. Проверка дубликатов
    words_to_process = check_input_duplicates(input_file)
    
    # 2. Генерация
    if words_to_process:
        generator.create_deck(words_to_process)
    else:
        print(f"Нет новых слов в {input_file}")