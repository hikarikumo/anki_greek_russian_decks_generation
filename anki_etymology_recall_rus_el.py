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
from pydantic import BaseModel, Field
from typing import List

# === ЗАГРУЗКА .ENV ===
load_dotenv()

# === НАСТРОЙКИ ===
input_file = "greek_text.txt"  # Файл, куда вставляем греческие предложения

# anki_deck_name = "Greek decks::Этимология::Linq recall (Русский -> Ελληνικά)"
# input_words_archive = "input_archive_sentences"
# output_deck = "linq_etymology_recall_rus_el.apkg"

# anki_deck_name = "Greek decks::Ελληνικά::Судан recall глаголы (Русский -> Ελληνικά)"
# output_deck = "sudan_recall_Ρήματα.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά::Судан recall местоимения (Русский -> Ελληνικά)"
# output_deck = "sudan_recall_prepositions.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά με easy Greek:: recall επαγγέλματα (Русский -> Ελληνικά)"
# output_deck = "recall_professions.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά με easy Greek:: recall What should Greek beginners listen (Русский -> Ελληνικά)"
# output_deck = "recall_easy_greek_what_should_greek_beginners_listen.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall Β1 με Ιαν ΚΕΓ (Русский -> Ελληνικά)"
# output_deck = "recall_β1_με_Ιαν_ΚΕΓ.apkg"
# input_words_archive = "input_words_archive/"

anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall Β1 γραφετικα - создание письма (Русский -> Ελληνικά)"
output_deck = "recall_β1_γραφετικα.apkg"
input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall Β1 2015 ΚΕΓ (Русский -> Ελληνικά)"
# output_deck = "recall_β1_2015_ΚΕΓ.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά με τον Ιαν:: recall ρήμ β2 (Русский -> Ελληνικά)"
# output_deck = "recall_verbs_b2.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά με τον Ιαν:: recall λεξιλόγιο γραμματικής (Русский -> Ελληνικά)"
# output_deck = "recall_εξεταση_λεξιλόγιο_γραμματικής.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά με easy Greek:: recall λεξιλόγιο are Greek Europeans (Русский -> Ελληνικά)"
# output_deck = "recall_easy_greek_λεξιλόγιο_are_greek_europeans.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά για Κυπρο:: recall λεξιλόγιο πολιτισμος (Русский -> Ελληνικά)"
# output_deck = "recall_Κυπρος_λεξιλόγιο_πολιτισμος.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά :: recall Γνώσεις για την Κύπρο (Русский -> Ελληνικά)"
# output_deck = "recall_γνώσεις_για_την_κύπρο.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall T2 my day (Русский -> Ελληνικά)"
# output_deck = "recall_T2_my_day.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall describe picture (Русский -> Ελληνικά)"
# output_deck = "recall_describe_picture.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Этимология::Linq recall 15.. (Русский -> Ελληνικά)"
# input_words_archive = "input_archive_sentences"
# output_deck = "linq_etymology_recall_rus_el.apkg"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: recall союзы (Русский -> Ελληνικά)"
# output_deck = "recall_unions.apkg"
# input_words_archive = "input_words_archive/"

# Уникальные ID для модели и колоды
GREEK_MODEL_ID = 1847592034
DECK_ID = 2159400556


# === PYDANTIC СХЕМЫ ДЛЯ STRUCTURED OUTPUTS ===
class ExampleItem(BaseModel):
    greek: str
    russian: str

class GreekCardSchema(BaseModel):
    transcription: str
    translation: str
    main_word_with_article: str
    meanings_official: List[str]
    meanings_colloquial: List[str]
    etymology_breakdown: str
    origin: str
    emotional_phrase: str
    examples: List[ExampleItem]


class GreekRecallGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        self.model = genanki.Model(
            GREEK_MODEL_ID,
            'Greek Recall Ultimate Model',
            fields=[
                {"name": "RussianTranslation"}, # Вопрос (Front)
                {"name": "GreekSentence"},      # Ответ (Back)
                {"name": "Transcription"},
                {"name": "MainWordWithArticle"},
                {"name": "MeaningsHTML"},
                {"name": "Audio"},
                {"name": "EtymologyBreakdown"},
                {"name": "Origin"},
                {"name": "EmotionalPhrase"},
                {"name": "ExamplesHTML"},
            ],
            templates=[
                {
                    "name": "Recall (Russian -> Greek Ultimate)",
                    "qfmt": """
                        <div class="card-content front-side">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{RussianTranslation}}</div>
                        </div>
                    """,
                    "afmt": """
                        <div class="card-content">
                            <div class="label">Как это по-гречески?</div>
                            <div class="meaning">{{RussianTranslation}}</div>
                            <hr class="main-divider">
                            
                            <div class="greek-text">{{GreekSentence}}</div>
                            <div class="transcription">[{{Transcription}}]</div>
                            <div class="audio-btn">{{Audio}}</div>
                            
                            <div class="word-focus-section">
                                <div class="main-word">{{MainWordWithArticle}}</div>
                                <div class="meanings-box">{{MeaningsHTML}}</div>
                            </div>

                            <hr>
                            <div class="etymology-section">
                                <h3>📖 Этимология и разбор:</h3>
                                <p><b>Разбор:</b> {{EtymologyBreakdown}}</p>
                                <p><b>Происхождение:</b> {{Origin}}</p>
                                <div class="emotional-phrase">✨ {{EmotionalPhrase}}</div>
                            </div>
                            
                            <hr>
                            <div class="examples-section">
                                <h3>📝 Примеры:</h3>
                                {{ExamplesHTML}}
                            </div>
                        </div>
                    """,
                },
            ],
            css="""
                .card { font-family: 'Segoe UI', Arial, sans-serif; font-size: 20px; text-align: center; color: #333; background-color: #f4f7f6; }
                .card-content { padding: 20px; }
                .front-side { display: flex; flex-direction: column; justify-content: center; min-height: 40vh; }
                
                .label { font-size: 14px; color: #888; text-transform: uppercase; margin-bottom: 15px; letter-spacing: 1px; }
                .meaning { font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;}
                .main-divider { border: 0; height: 2px; background: #0045ad; margin: 25px 0; }
                
                .greek-text { font-size: 34px; font-weight: bold; color: #0045ad; margin-bottom: 5px; }
                .transcription { color: #7f8c8d; font-size: 20px; font-style: italic; margin-bottom: 15px; }
                .audio-btn { margin: 15px 0; }
                hr { border: 0; height: 1px; background: #dcdde1; margin: 20px 0; }
                
                /* Секция главного слова */
                .word-focus-section { background: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 5px solid #00a8ff; margin-bottom: 20px; text-align: left; }
                .main-word { font-size: 28px; font-weight: bold; color: #0097e6; margin-bottom: 10px; text-align: center; }
                .meanings-box { font-size: 18px; line-height: 1.5; }
                .meanings-title { font-weight: bold; color: #2f3640; margin-top: 10px; }
                .meanings-list { margin: 5px 0 0 20px; padding: 0; }
                
                /* Секция этимологии */
                .etymology-section { text-align: left; background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
                .etymology-section h3 { color: #2c3e50; font-size: 20px; margin-top: 0; border-bottom: 2px solid #f1c40f; display: inline-block; padding-bottom: 3px; }
                .etymology-section p { font-size: 18px; line-height: 1.4; margin: 8px 0; }
                .emotional-phrase { margin-top: 15px; font-size: 20px; font-weight: bold; color: #e15f41; font-style: italic; text-align: center; }
                
                /* Секция примеров */
                .examples-section { text-align: left; background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
                .examples-section h3 { color: #2c3e50; font-size: 20px; margin-top: 0; border-bottom: 2px solid #2ecc71; display: inline-block; padding-bottom: 3px; }
                .example-item { margin-bottom: 15px; border-bottom: 1px dashed #eee; padding-bottom: 10px; }
                .example-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
                .example-header { display: flex; align-items: center; justify-content: space-between; }
                .example-greek { font-size: 20px; color: #0045ad; font-weight: 500; flex: 1; }
                .example-russian { font-size: 16px; color: #7f8c8d; font-style: italic; margin-top: 5px; }
            """,
        )

        self.deck = genanki.Deck(DECK_ID, anki_deck_name)
        self.media_files = []
        if not os.path.exists("media_files"): os.makedirs("media_files")

    def get_card_data(self, text):
        """Получаем полный разбор предложения через Gemini со строгой валидацией Pydantic"""
        if not self.client: return None
        try:
            prompt = f"""
            Analyze the following Greek text: '{text}'.
            Identify the MAIN word (especially if it's a verb or a key noun).
            Return ONLY a SINGLE valid JSON object (NOT an array/list) with the exact following structure:
            {{
                "transcription": "Русская транскрипция всего исходного текста (с ударениями, если возможно)",
                "translation": "Перевод исходного текста на русский язык",
                "main_word_with_article": "Главное слово в начальной форме с определенным артиклем (например, 'το σπίτι', 'ο δρόμος', или просто глагол с частицей 'να' или 'εγώ', если уместно)",
                "meanings_official": ["Официальное значение 1", "Официальное значение 2"],
                "meanings_colloquial": ["Разговорное или сленговое значение 1", "Переносный смысл (если есть)"],
                "etymology_breakdown": "Этимологический разбор главного слова (корни, предлоги, приставки, суффиксы - на русском)",
                "origin": "1-2 предложения на русском о происхождении слова",
                "emotional_phrase": "Очень краткая, хлесткая и эмоциональная ассоциация для запоминания сути этимологии. СТРОГО 2-3 СЛОВА на русском (например: 'Вместе лицом к лицу!', 'Совместное столкновение!')",
                "examples": [
                    {{
                        "greek": "Пример предложения 1 на греческом  (с использованием этого слова) для использования в реальной жизни. Сделай его максимально естественным и живым, как если бы ты хотел показать это слово другу в разговоре или в тексте. СТРОГО вся использованная лексика уровня А2",
                        "russian": "Перевод примера 1 на русский"
                    }},
                    {{
                        "greek": "Пример предложения 2 на греческом (с использованием этого слова) для использования в реальной жизни. Сделай его максимально естественным и живым, как если бы ты хотел показать это слово другу в разговоре или в тексте. СТРОГО вся использованная лексика уровня А2",
                        "russian": "Перевод примера 2 на русский"
                    }}
                ]
            }}
            """
            response = self.client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=GreekCardSchema  # Принудительно заставляем API следовать Pydantic схеме
                )
            )
            
            # Валидируем через Pydantic и возвращаем как классический dict, 
            # чтобы не менять логику обработки полей ниже
            validated_data = GreekCardSchema.model_validate_json(response.text)
            return validated_data.model_dump()
            
        except Exception as e:
            print(f"⚠️ Ошибка API или JSON валидации: {e}")
            return None

    def get_tts(self, text):
        """Генерация аудио для греческого текста"""
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
        
        data = self.get_card_data(greek_sentence)
        if not data:
            print(f"❌ Пропуск {greek_sentence[:50]}... из-за ошибки генерации.")
            return
            
        transcription = data.get("transcription", "")
        russian_text = data.get("translation", "???")
        main_word = data.get("main_word_with_article", "")
        etymology_breakdown = data.get("etymology_breakdown", "Нет данных.")
        origin = data.get("origin", "Нет данных.")
        emotional_phrase = data.get("emotional_phrase", "Без эмоций 🤖")
        
        # --- Сборка значений ---
        off_meanings = data.get("meanings_official", [])
        col_meanings = data.get("meanings_colloquial", [])
        
        meanings_html = ""
        if off_meanings:
            meanings_html += "<div class='meanings-title'>📚 Официальные значения:</div><ul class='meanings-list'>"
            for m in off_meanings: meanings_html += f"<li>{m}</li>"
            meanings_html += "</ul>"
            
        if col_meanings and len(col_meanings) > 0 and col_meanings[0].strip():
            meanings_html += "<div class='meanings-title'>🗣 Разговорные/Сленг:</div><ul class='meanings-list'>"
            for m in col_meanings: meanings_html += f"<li>{m}</li>"
            meanings_html += "</ul>"

        # --- Аудио и примеры ---
        audio = self.get_tts(greek_sentence)

        examples_list = data.get("examples", [])
        examples_html = ""
        for ex in examples_list:
            ex_gr = ex.get("greek", "")
            ex_ru = ex.get("russian", "")
            if not ex_gr: continue
            
            ex_audio = self.get_tts(ex_gr)
            examples_html += f"""
            <div class="example-item">
                <div class="example-header">
                    <span class="example-greek">{ex_gr}</span>
                    <span class="audio-btn">{ex_audio}</span>
                </div>
                <div class="example-russian">{ex_ru}</div>
            </div>
            """

        note = genanki.Note(
            model=self.model,
            fields=[
                russian_text,          # Front: Русский перевод
                greek_sentence,        # Back: Греческий оригинал
                transcription, 
                main_word, 
                meanings_html, 
                audio,                 # Back: Озвучка оригинала
                etymology_breakdown, 
                origin, 
                emotional_phrase, 
                examples_html
            ]
        )
        self.deck.add_note(note)
        time.sleep(1) # Задержка для API

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
        print(f"Файл пуст. Добавьте греческие предложения в {input_file}")