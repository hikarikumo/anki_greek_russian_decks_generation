import genanki
import os
import time
import json
from google import genai
from google.genai import types
from datetime import datetime
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

# === НАСТРОЙКИ ===
input_file = "greek_words.txt"

# anki_deck_name = "Greek decks::GreekPod101::Greek Recall (Russian -> Greek) Greekpod101 simple dialogues"
# output_deck = "greekpod101_simple_dialogues_recall.apkg"
# input_words_archive = "input_words_archive_greekpod101_simple_dialogues_recall"

# anki_deck_name = "Greek Recall (Russian -> Greek) Zero Matrix"
# output_deck = "recall_zero_matrix.apkg"
# input_words_archive = "input_words_archive_recall_zero_matrix"

# anki_deck_name = "Greek decks::Ελληνικά::recall 100 самых частотных глаголов (Русский -> Ελληνηκα)"
# output_deck = "recall_100_most_frequent_greek_verbs.apkg"
# input_words_archive = "input_words_archive_recall_100_most_frequent_greek_verbs"

# anki_deck_name = "Greek decks::Ελληνικά::recall цифры (Русский -> Ελληνηκα)"
# output_deck = "recall_numbers.apkg"
# input_words_archive = "input_words_archive_recall_numbers"

# anki_deck_name = "Greek decks::Ελληνικά::recall глаголы этап 1 (Русский -> Ελληνηκα)"
# output_deck = "recall_verbs1.apkg"
# input_words_archive = "input_words_archive_recall_verbs1"

# anki_deck_name = "Greek decks::Ελληνικά::recall грамматика 1 (Русский -> Ελληνηκα)"
# output_deck = "recall_grammar1.apkg"
# input_words_archive = "input_words_archive_recall_grammar1"

# anki_deck_name = "Greek decks::Ελληνικά::recall грамматика 2 это (Русский -> Ελληνηκα)"
# output_deck = "recall_grammar2_this.apkg"
# input_words_archive = "input_words_archive_recall_grammar2_this"

# anki_deck_name = "Greek decks::Ελληνικά::recall грамматика 3 это (Русский -> Ελληνηκα)"
# output_deck = "recall_grammar3_this.apkg"
# input_words_archive = "input_words_archive_recall_grammar3_this"

# anki_deck_name = "Greek decks::Ελληνικά::Судан лексика 01 (Русский -> Ελληνηκα)"
# output_deck = "recall_sudan_vocabulary_01.apkg"
# input_words_archive = "input_words_archive/recall_sudan_vocabulary_01"

# anki_deck_name = "Greek decks::Ελληνικά::Судан лексика 02 (Русский -> Ελληνηκα)"
# output_deck = "recall_sudan_vocabulary_02.apkg"
# input_words_archive = "input_words_archive/recall_sudan_vocabulary_02"

# anki_deck_name = "Greek decks::Ελληνικά::recall быть (Русский -> Ελληνηκα)"
# output_deck = "recall_to_be.apkg"
# input_words_archive = "input_words_archive/recall_to_be_ειμαι"

# anki_deck_name = "Greek decks::Ελληνικά::recall soudan 02(Русский -> Ελληνηκα)"
# output_deck = "recall_soudan_03.apkg"
# input_words_archive = "input_words_archive/recall_soudan_03"

anki_deck_name = "Greek decks::Ελληνικά::recall эри 01 (Русский -> Ελληνηκα)"
output_deck = "recall_eri_01.apkg"
input_words_archive = "input_words_archive/recall_eri_01"

GREEK_MODEL_ID = 1847592033
DECK_ID = 2159400555

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
                {"name": "GreekWord"},      # Ответ
                {"name": "Translation"},    # Вопрос
                {"name": "WordAudio"},      # TTS
                {"name": "Example"},
                {"name": "ExampleTrans"},
                {"name": "ExampleAudio"},   # TTS
            ],
            templates=[
                {
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
                .label { font-size: 14px; color: #888; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
                .meaning { font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; }
                .greek-word { font-family: "Helvetica", sans-serif; font-size: 42px; font-weight: bold; color: #0045ad; margin: 15px 0; }
                .example-box { margin-top: 25px; padding: 15px; background-color: #f4f9ff; border-radius: 8px; border-left: 5px solid #0045ad; text-align: left; }
                .example-greek { font-size: 20px; color: #000; margin-bottom: 6px; line-height: 1.4; }
                .example-trans { font-size: 16px; color: #666; font-style: italic; }
                .audio-btn { margin-top: 10px; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        if not os.path.exists("media_files"): os.makedirs("media_files")

    def get_gemini_data(self, word):
        if not self.client: return None
        try:
            prompt = (
                f"You are a Greek tutor. Target word: '{word}'. "
                "1. Russian translation. "
                "2. Simple Greek example sentence. "
                "3. Russian translation of example. "
                "Respond JSON: {\"translation\": \"...\", \"example_greek\": \"...\", \"example_russian\": \"...\"}"
            )
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            if response.text: return json.loads(response.text)
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
        return None

    def get_tts_audio(self, text, prefix):
        """Единый TTS метод"""
        if not text: return ""
        safe_prefix = "".join([c for c in prefix if c.isalnum()])[:10]
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
            print(f"⚠️ TTS error: {e}")
            return ""

    def process_word(self, word):
        print(f"\n🔹 Обработка (Recall): {word}")
        ai_data = self.get_gemini_data(word)
        
        translation = "???"
        example_el = ""
        example_ru = ""

        if ai_data:
            translation = ai_data.get("translation", "???")
            example_el = ai_data.get("example_greek", "")
            example_ru = ai_data.get("example_russian", "")
            print(f"   📖 Перевод: {translation}")
        
        # 1. Аудио Слова (TTS)
        word_audio = self.get_tts_audio(word, "word_rc")
        
        # 2. Аудио Примера (TTS)
        ex_audio = ""
        if example_el:
            ex_audio = self.get_tts_audio(example_el, "ex_rc")

        note = genanki.Note(
            model=self.model,
            fields=[word, translation, word_audio, example_el, example_ru, ex_audio]
        )
        self.deck.add_note(note)
        time.sleep(1)

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
        with open(f"{input_words_archive}/greek_recall_{timestamp}.txt", "w", encoding="utf-8") as f: f.write(content)
        with open(input_file, "w", encoding="utf-8") as f: f.write("")

def check_input_duplicates(filename):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f: f.write("ευχαριστώ\n")
        return ["ευχαριστώ"]

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