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
anki_deck_name = "Greek decks::GreekPod101::GreekPod 101 simple dialogues (Greek -> Russian)"
output_deck = "greekpod101_simple_dialogues.apkg"
input_words_archive = "input_words_archive_greekpod101_simple_dialogues"
# anki_deck_name = "Greek Zero Matrix (Greek -> Russian)"
# output_deck = "zero_matrix.apkg"
# input_words_archive = "input_words_archive_zero_matrix"


GREEK_MODEL_ID = 1607392320
DECK_ID = 2059400120

class GreekAnkiGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("❌ ОШИБКА: GOOGLE_API_KEY не найден.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        self.model = genanki.Model(
            GREEK_MODEL_ID,
            anki_deck_name,
            fields=[
                {"name": "GreekWord"},
                {"name": "Translation"},
                {"name": "WordAudio"},      # Теперь это TTS
                {"name": "Example"},
                {"name": "ExampleTrans"},
                {"name": "ExampleAudio"},   # И это TTS
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
                        <hr>
                        <div class="meaning">{{Translation}}</div>
                        <div class="example-box">
                            <div class="example">{{Example}} {{ExampleAudio}}</div>
                            <div class="example-meaning">{{ExampleTrans}}</div>
                        </div>
                    """,
                }
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
        if not self.client: return None
        try:
            prompt = (
                f"You are a Greek language teacher. Word: '{word}'. "
                "1. Translate to Russian. "
                "2. Create a simple Greek example sentence. "
                "3. Translate example to Russian. "
                "Respond JSON: {\"translation\": \"...\", \"example_greek\": \"...\", \"example_russian\": \"...\"}"
            )
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            if response.text: return json.loads(response.text)
        except Exception as e:
            print(f"⚠️ Ошибка Gemini: {e}")
        return None

    def get_tts_audio(self, text, prefix):
        """Единая функция для генерации аудио (и слов, и предложений)"""
        if not text: return ""
        
        # Очистка имени файла
        safe_prefix = "".join([c for c in prefix if c.isalnum()])[:10]
        # Используем хеш текста для уникальности или timestamp
        safe_text = "".join([c for c in text if c.isalnum()])[:15]
        timestamp = int(time.time())
        
        filename = f"tts_{safe_prefix}_{safe_text}_{timestamp}.mp3"
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
        print(f"\n🔹 Обработка: {word}")
        ai_data = self.get_gemini_data(word)
        
        translation = "???"
        example_el = ""
        example_ru = ""
        
        if ai_data:
            translation = ai_data.get("translation", "???")
            example_el = ai_data.get("example_greek", "")
            example_ru = ai_data.get("example_russian", "")
            print(f"   📖 Перевод: {translation}")

        # 1. Аудио СЛОВА (теперь TTS)
        word_audio = self.get_tts_audio(word, "word")

        # 2. Аудио ПРИМЕРА (TTS)
        ex_audio = ""
        if example_el:
            ex_audio = self.get_tts_audio(example_el, "ex")

        note = genanki.Note(
            model=self.model,
            fields=[word, translation, word_audio, example_el, example_ru, ex_audio]
        )
        self.deck.add_note(note)
        time.sleep(1) # Пауза для стабильности

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
        with open(input_file, "r", encoding="utf-8") as f: content = f.read()
        with open(f"{input_words_archive}/greek_{timestamp}.txt", "w", encoding="utf-8") as f: f.write(content)
        with open(input_file, "w", encoding="utf-8") as f: f.write("")

def check_input_duplicates(filename):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f: f.write("καλημέρα\n")
        return ["καλημέρα"]
    
    archived = set()
    if os.path.exists(input_words_archive):
        for f in os.listdir(input_words_archive):
            with open(os.path.join(input_words_archive, f), "r", encoding="utf-8") as file:
                for line in file: archived.add(line.strip())
                
    with open(filename, "r", encoding="utf-8") as f:
        current = list(set([l.strip() for l in f if l.strip()]))
        
    final = [w for w in current if w not in archived]
    print(f"Новых слов: {len(final)}")
    return final

if __name__ == "__main__":
    gen = GreekAnkiGenerator()
    words = check_input_duplicates(input_file)
    if words: gen.create_deck(words)
    else: print("Нет новых слов.")