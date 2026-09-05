"""Build a B1 Modern Greek chunk deck: Greek -> Russian.

Input file (default: greek_text.txt) accepts one item per line in three forms:

1. Recommended JSONL:
   {"target":"θέτω σε κίνδυνο","source_sentence":"Η απόφαση έθεσε το σχέδιο σε κίνδυνο.","source":"book ch. 4","theme":"environment","priority":"active"}
2. TSV: target<TAB>source_sentence<TAB>source<TAB>theme<TAB>priority
3. A plain Greek sentence. Gemini will select one reusable B1 chunk.

The script never clears or archives the input. build_chunk_decks.py does that only
after both directional decks have been built successfully.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Literal

import genanki
from dotenv import load_dotenv
from google import genai
from google.genai import types
from gtts import gTTS
from pydantic import BaseModel, Field


load_dotenv()

INPUT_FILE = Path(os.getenv("ANKI_CHUNKS_INPUT", "greek_text.txt"))
OUTPUT_DECK = Path(os.getenv("ANKI_CHUNKS_EL_RU_OUTPUT", "b1_chunks_el_rus.apkg"))
ANKI_DECK_NAME = os.getenv(
    "ANKI_CHUNKS_EL_RU_NAME",
    "Greek decks::Ελληνικά Chunks Β1::Chunks Original(Ελληνικά - Русский)",
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
API_DELAY_SECONDS = float(os.getenv("GEMINI_DELAY_SECONDS", "0.5"))
MEDIA_DIR = Path(os.getenv("ANKI_MEDIA_DIR", "media_files"))
CACHE_DIR = Path(os.getenv("ANKI_CHUNKS_CACHE", ".chunk_cache"))
FAILED_FILE = Path("failed_chunks_el_rus.jsonl")

MODEL_ID = 1876041101
DECK_ID = 2076041101
PROMPT_VERSION = "b1-chunks-v1"


class ChunkInput(BaseModel):
    target: str = ""
    source_sentence: str
    source: str = ""
    theme: str = "general"
    priority: Literal["active", "recognition", "auto"] = "active"


class ChunkAnalysis(BaseModel):
    target_surface: str
    canonical_chunk: str
    meaning_ru: str
    production_cue_ru: str
    literal_gloss_ru: str = ""
    source_translation_ru: str
    source_transcription_ru: str
    transfer_sentence_el: str
    transfer_sentence_ru: str
    transfer_transcription_ru: str
    grammar_ru: str
    register_ru: str
    word_family: list[str] = Field(default_factory=list)
    etymology_breakdown_ru: str
    origin_ru: str
    emotional_hook_ru: str
    recommended_priority: Literal["active", "recognition"]


def load_items(path: Path) -> list[ChunkInput]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден входной файл: {path}")

    items: list[ChunkInput] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if line.startswith("{"):
                items.append(ChunkInput.model_validate_json(line))
            elif "\t" in line:
                parts = [part.strip() for part in line.split("\t")]
                parts += [""] * (5 - len(parts))
                target, sentence, source, theme, priority = parts[:5]
                items.append(
                    ChunkInput(
                        target=target,
                        source_sentence=sentence,
                        source=source,
                        theme=theme or "general",
                        priority=priority or "active",
                    )
                )
            else:
                items.append(ChunkInput(source_sentence=line))
        except Exception as exc:
            raise ValueError(f"Ошибка в строке {line_number}: {exc}") from exc

    if not items:
        raise ValueError(f"Файл {path} пуст")
    return items


def prompt_for(item: ChunkInput) -> str:
    target_instruction = (
        f"The learner selected this target: {item.target!r}. Analyze this exact lexical chunk "
        "in the meaning it has in the source sentence. target_surface must reproduce its form "
        "from the sentence, while canonical_chunk gives the reusable dictionary-like form."
        if item.target
        else
        "Select exactly ONE useful, reusable B1 lexical chunk from the sentence. Prefer a natural "
        "collocation, verb pattern, connector, or fixed phrase over an isolated easy word."
    )
    return f"""
You create rigorous Anki material for a Russian-speaking learner of Standard Modern Greek at B1.

SOURCE SENTENCE: {item.source_sentence!r}
SOURCE LABEL: {item.source!r}
THEME: {item.theme!r}
{target_instruction}

Return one object matching the supplied schema. Requirements:
- Explain the chunk only in the exact sense used in the source sentence.
- canonical_chunk must include required prepositions/articles/particles and show a reusable form.
- meaning_ru is the natural contextual translation; production_cue_ru is a short, unambiguous
  Russian cue that can elicit the Greek chunk during active recall.
- Give a faithful Russian translation and readable Russian transcription of the source sentence.
- Create exactly one transfer sentence in a DIFFERENT realistic context, 8-18 Greek words,
  natural Standard Modern Greek, around B1, using the same chunk (inflect it if grammar requires).
- grammar_ru must explain the construction and government, not retell basic school grammar.
- word_family contains at most four genuinely useful related Greek forms with brief Russian glosses.
- etymology_breakdown_ru and origin_ru must be accurate and concise. Never invent an etymology;
  if uncertain, write "Надёжной подсказки нет".
- register_ru states register and important usage restrictions.
- emotional_hook_ru is a vivid but accurate 2-6 word Russian memory hook.
- Correct Greek accents and punctuation. Do not simplify the target below B1.
""".strip()


def cache_path(item: ChunkInput) -> Path:
    payload = json.dumps(
        {"version": PROMPT_VERSION, "model": GEMINI_MODEL, "item": item.model_dump()},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def analyze(client: genai.Client, item: ChunkInput) -> ChunkAnalysis:
    path = cache_path(item)
    if path.exists():
        return ChunkAnalysis.model_validate_json(path.read_text(encoding="utf-8"))

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_for(item),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChunkAnalysis,
                    temperature=0.25,
                ),
            )
            data = ChunkAnalysis.model_validate_json(response.text)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".tmp")
            temp.write_text(data.model_dump_json(indent=2), encoding="utf-8")
            os.replace(temp, path)
            return data
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Gemini не обработал карточку после 3 попыток: {last_error}")


def audio_for(text: str, media_files: list[str]) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    filename = f"el_{digest}.mp3"
    path = MEDIA_DIR / filename
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                gTTS(text=text, lang="el").save(str(path))
                break
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt * 2)
        else:
            raise RuntimeError(f"TTS не создал аудио: {last_error}")

    path_string = str(path)
    if path_string not in media_files:
        media_files.append(path_string)
    return f"[sound:{filename}]"


def safe(value: str) -> str:
    return html.escape(value or "", quote=True).replace("\n", "<br>")


def highlighted(sentence: str, surface: str) -> str:
    if not surface:
        return safe(sentence)
    match = re.search(re.escape(surface), sentence, flags=re.IGNORECASE)
    if not match:
        return safe(sentence)
    return (
        safe(sentence[: match.start()])
        + "<mark>"
        + safe(sentence[match.start() : match.end()])
        + "</mark>"
        + safe(sentence[match.end() :])
    )


def list_html(values: list[str]) -> str:
    if not values:
        return "<span class='muted'>—</span>"
    return "<ul>" + "".join(f"<li>{safe(value)}</li>" for value in values) + "</ul>"


def tag(value: str) -> str:
    return re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE).strip("_")


CSS = """
.card { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 19px; text-align: left; padding: 18px; background: #f5f7f8; color: #263238; }
.chunk { color: #0757a6; font-size: 31px; font-weight: 750; text-align: center; margin: 6px 0 18px; }
.sentence { font-size: 24px; line-height: 1.45; text-align: center; background: white; padding: 16px; border-radius: 10px; }
mark { background: #fff1a8; color: inherit; padding: 0 3px; border-radius: 3px; }
.audio { text-align: center; margin: 12px; }
.meaning { color: #183b56; font-size: 25px; font-weight: 700; text-align: center; margin: 14px 0; }
.box { background: white; border-left: 5px solid #2f80ed; border-radius: 8px; padding: 13px 15px; margin: 13px 0; line-height: 1.45; }
.transfer { border-left-color: #27ae60; }.memory { border-left-color: #f2c94c; }.meta { border-left-color: #9b51e0; }
.label { color: #607d8b; font-size: 14px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 5px; }
.ru { color: #546e7a; font-size: 17px; margin-top: 6px; }.transcription { color: #78909c; font-size: 16px; font-style: italic; margin-top: 6px; }
details summary { cursor: pointer; color: #455a64; font-weight: 700; }.muted { color: #90a4ae; } ul { margin: 7px 0; padding-left: 24px; }
"""


def make_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "B1 Greek Lexical Chunks EL-RU v1",
        fields=[
            {"name": name}
            for name in [
                "CanonicalChunk", "SourceSentenceHTML", "SourceSentenceEL", "MeaningRU",
                "ProductionCueRU", "LiteralGlossRU", "SourceTranslationRU",
                "SourceTranscriptionRU", "TransferSentenceEL", "TransferSentenceRU",
                "TransferTranscriptionRU", "SourceAudio", "TransferAudio", "GrammarRU",
                "RegisterRU", "WordFamilyHTML", "EtymologyRU", "OriginRU", "MemoryHookRU",
                "SourceLabel", "Theme", "Priority",
            ]
        ],
        templates=[{
            "name": "Chunk: Ελληνικά → Русский",
            "qfmt": """
                <div class="chunk">{{CanonicalChunk}}</div>
                <div class="sentence">{{SourceSentenceHTML}}</div>
                <div class="audio">{{SourceAudio}}</div>
            """,
            "afmt": """
                {{FrontSide}}<hr>
                <div class="meaning">{{MeaningRU}}</div>
                <div class="box"><div class="label">Перевод исходной фразы</div>{{SourceTranslationRU}}<div class="transcription">[{{SourceTranscriptionRU}}]</div></div>
                <div class="box transfer"><div class="label">Перенос в другой контекст</div><b>{{TransferSentenceEL}}</b><div class="audio">{{TransferAudio}}</div><div class="ru">{{TransferSentenceRU}}</div><div class="transcription">[{{TransferTranscriptionRU}}]</div></div>
                <div class="box memory"><div class="label">Точная подсказка для воспроизведения</div>{{ProductionCueRU}}<br><span class="ru">Дословно: {{LiteralGlossRU}}</span></div>
                <details><summary>Грамматика, употребление и этимология</summary>
                  <div class="box meta"><b>Конструкция:</b> {{GrammarRU}}<br><b>Регистр:</b> {{RegisterRU}}<br><b>Семья:</b> {{WordFamilyHTML}}<br><b>Разбор:</b> {{EtymologyRU}}<br><b>Происхождение:</b> {{OriginRU}}<br><b>Крючок:</b> {{MemoryHookRU}}</div>
                </details>
                <div class="ru">Источник: {{SourceLabel}} · Тема: {{Theme}} · Приоритет: {{Priority}}</div>
            """,
        }],
        css=CSS,
    )


def build(items: list[ChunkInput]) -> None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Не задан GOOGLE_API_KEY (проверь .env)")

    client = genai.Client(api_key=api_key)
    model = make_model()
    deck = genanki.Deck(DECK_ID, ANKI_DECK_NAME)
    media_files: list[str] = []
    failures: list[dict[str, object]] = []

    for index, item in enumerate(items, 1):
        print(f"🔹 {index}/{len(items)}: {item.target or item.source_sentence[:55]}")
        try:
            data = analyze(client, item)
            source_audio = audio_for(item.source_sentence, media_files)
            transfer_audio = audio_for(data.transfer_sentence_el, media_files)
            priority = item.priority if item.priority != "auto" else data.recommended_priority
            fields = [
                safe(data.canonical_chunk), highlighted(item.source_sentence, data.target_surface),
                safe(item.source_sentence), safe(data.meaning_ru), safe(data.production_cue_ru),
                safe(data.literal_gloss_ru), safe(data.source_translation_ru),
                safe(data.source_transcription_ru), safe(data.transfer_sentence_el),
                safe(data.transfer_sentence_ru), safe(data.transfer_transcription_ru),
                source_audio, transfer_audio, safe(data.grammar_ru), safe(data.register_ru),
                list_html(data.word_family), safe(data.etymology_breakdown_ru), safe(data.origin_ru),
                safe(data.emotional_hook_ru), safe(item.source or "—"), safe(item.theme), safe(priority),
            ]
            note = genanki.Note(
                model=model,
                fields=fields,
                guid=genanki.guid_for("chunks-el-ru", item.source_sentence, data.canonical_chunk),
                tags=[value for value in ["b1_chunk", tag(item.theme), tag(priority)] if value],
            )
            deck.add_note(note)
            time.sleep(API_DELAY_SECONDS)
        except Exception as exc:
            print(f"❌ {exc}")
            failures.append({"item": item.model_dump(), "error": str(exc)})

    if failures:
        FAILED_FILE.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in failures) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError(
            f"Не обработано карточек: {len(failures)}. Подробности: {FAILED_FILE}. "
            "Входной файл сохранён; успешные ответы уже находятся в кэше."
        )

    if FAILED_FILE.exists():
        FAILED_FILE.unlink()
    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(str(OUTPUT_DECK))
    print(f"✅ Колода создана: {OUTPUT_DECK} ({len(items)} карточек)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="проверить входной файл без API")
    args = parser.parse_args()
    try:
        items = load_items(INPUT_FILE)
        if args.validate_only:
            print(f"✅ Формат корректен: {len(items)} элементов в {INPUT_FILE}")
            return 0
        build(items)
        return 0
    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
