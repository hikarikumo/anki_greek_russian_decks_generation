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
input_file = "greek_text.txt"  

# anki_deck_name = "Greek decks::Этимология::Linq (Ελληνηκα - Русский)"
# input_words_archive = "input_archive_sentences"
# output_deck = "linq_etymology_el_rus.apkg"

# anki_deck_name = "Greek decks::Ελληνικά::Судан глаголы (Ελληνηκα - Русский)"
# output_deck = "sudan_Ρήματα.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά::Судан местоимения (Ελληνηκα - Русский)"
# output_deck = "sudan_prepositions.apkg"
# input_words_archive = "input_words_archive/"

anki_deck_name = "Greek decks::Ελληνικά με τον Ιαν:: Actions & Change (Ελληνηκα - Русский)"
output_deck = "actions_change.apkg"
input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: T2 my day (Ελληνηκα - Русский)"
# output_deck = "T2_my_day.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: describe picture (Ελληνηκα - Русский)"
# output_deck = "describe_picture.apkg"
# input_words_archive = "input_words_archive/"

# anki_deck_name = "Greek decks::Этимология::Linq 15.. (Ελληνηκα - Русский)"
# input_words_archive = "input_archive_sentences"
# output_deck = "linq_etymology_el_rus.apkg"

# anki_deck_name = "Greek decks::Ελληνικά έξεταση:: союзы (Ελληνηκα - Русский)"
# output_deck = "unions.apkg"
# input_words_archive = "input_words_archive/"


MODEL_ID = 1607392321
DECK_ID = 2059400121

class GreekSentenceGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        self.model = genanki.Model(
            MODEL_ID,
            'Greek Ultimate Model',
            fields=[
                {"name": "Sentence"},
                {"name": "Transcription"},
                {"name": "Translation"},
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
                    "name": "Greek Sentence -> Russian (Ultimate)",
                    "qfmt": '<div class="greek-text">{{Sentence}}</div>',
                    "afmt": """
                        <div class="greek-text">{{Sentence}}</div>
                        <div class="transcription">[{{Transcription}}]</div>
                        <div class="audio-btn">{{Audio}}</div>
                        <hr>
                        <div class="translation">{{Translation}}</div>
                        
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
                    """,
                }
            ],
            css="""
                .card { font-family: 'Segoe UI', Arial, sans-serif; font-size: 20px; text-align: center; padding: 20px; background-color: #f4f7f6; color: #333; }
                .greek-text { color: #0045ad; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
                .transcription { color: #7f8c8d; font-size: 20px; font-style: italic; margin-bottom: 15px; }
                .translation { color: #2c3e50; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
                .audio-btn { margin: 15px 0; }
                hr { border: 0; height: 1px; background: #dcdde1; margin: 20px 0; }
                
                /* Секция главного слова и значений */
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
                            "greek": "Пример предложения 1 на греческом (с использованием этого слова) для использования в реальной жизни",
                            "russian": "Перевод примера 1 на русский"
                        }},
                        {{
                            "greek": "Пример предложения 2 на греческом (с использованием этого слова) для использования в реальной жизни",
                            "russian": "Перевод примера 2 на русский"
                        }}
                    ]
                }}
                """
                response = self.client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type='application/json')
                )
                
                # Парсим JSON
                parsed_data = json.loads(response.text)
                
                # 🛡 ПРЕДОХРАНИТЕЛЬ: Если Gemini вернул список, берем первый элемент
                if isinstance(parsed_data, list):
                    if len(parsed_data) > 0:
                        parsed_data = parsed_data[0]
                    else:
                        print("⚠️ Gemini вернул пустой список.")
                        return None
                
                # Если после всех проверок это все еще не словарь, отбраковываем
                if not isinstance(parsed_data, dict):
                    print(f"⚠️ Неожиданный формат данных от API: {type(parsed_data)}")
                    return None
                    
                return parsed_data
                
            except Exception as e:
                print(f"⚠️ Ошибка API или парсинга JSON: {e}")
                return None


    def get_tts(self, text):
            if not text: return ""
            txt_hash = hashlib.md5(text.encode()).hexdigest()[:10]
            filename = f"el_{txt_hash}.mp3"
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
        
        data = self.get_card_data(sentence)
        if not data:
            print("❌ Пропуск из-за ошибки генерации.")
            return
            
        transcription = data.get("transcription", "")
        translation = data.get("translation", "???")
        main_word = data.get("main_word_with_article", "")
        etymology_breakdown = data.get("etymology_breakdown", "Нет данных.")
        origin = data.get("origin", "Нет данных.")
        emotional_phrase = data.get("emotional_phrase", "Без эмоций 🤖")
        
        # --- Сборка значений (Официальные + Разговорные) ---
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
        main_audio = self.get_tts(sentence)

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
                sentence, 
                transcription, 
                translation, 
                main_word, 
                meanings_html, 
                main_audio, 
                etymology_breakdown, 
                origin, 
                emotional_phrase, 
                examples_html
            ]
        )
        self.deck.add_note(note)
        time.sleep(1) # Увеличил паузу до 1 сек, т.к. запрос стал тяжелее

    def create_deck(self, lines):
        for line in lines:
            self.process_line(line)
        
        pkg = genanki.Package(self.deck)
        pkg.media_files = self.media_files
        pkg.write_to_file(output_deck)
        print(f"\n✅ Готово! Колода: {output_deck}")

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
        print(f"Файл пуст. Добавьте текст в {input_file}")