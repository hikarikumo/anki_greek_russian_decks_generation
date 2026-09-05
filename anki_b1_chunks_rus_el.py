"""Build a B1 Modern Greek chunk recall deck: Russian -> Greek.

Uses the same input, Gemini schema, response cache and audio cache as
anki_b1_chunks_el_rus.py. Run both through build_chunk_decks.py so the input is archived
only after both packages have been created successfully.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import genanki
from dotenv import load_dotenv
from google import genai

from anki_b1_chunks_el_rus import (
    API_DELAY_SECONDS,
    INPUT_FILE,
    ChunkInput,
    analyze,
    audio_for,
    highlighted,
    list_html,
    load_items,
    safe,
    tag,
)


load_dotenv()

OUTPUT_DECK = Path(os.getenv("ANKI_CHUNKS_RU_EL_OUTPUT", "b1_chunks_recall_rus_el.apkg"))
ANKI_DECK_NAME = os.getenv(
    "ANKI_CHUNKS_RU_EL_NAME",
    "Greek decks::Ελληνικά Chunks Β1::Chunks Recall (Русский - Ελληνικά)",
)
FAILED_FILE = Path("failed_chunks_recall_rus_el.jsonl")

MODEL_ID = 1876041102
DECK_ID = 2076041102


CSS = """
.card { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 19px; text-align: left; padding: 18px; background: #f5f7f8; color: #263238; }
.task { color: #7b1fa2; font-size: 14px; font-weight: 750; letter-spacing: .05em; text-align: center; text-transform: uppercase; }
.cue { color: #183b56; font-size: 29px; font-weight: 750; text-align: center; margin: 12px 0 18px; }
.sentence { font-size: 22px; line-height: 1.45; text-align: center; background: white; padding: 16px; border-radius: 10px; }
.chunk { color: #0757a6; font-size: 32px; font-weight: 800; text-align: center; margin: 16px 0; }
mark { background: #fff1a8; color: inherit; padding: 0 3px; border-radius: 3px; }
.audio { text-align: center; margin: 12px; }
.box { background: white; border-left: 5px solid #2f80ed; border-radius: 8px; padding: 13px 15px; margin: 13px 0; line-height: 1.45; }
.transfer { border-left-color: #27ae60; }.memory { border-left-color: #f2c94c; }.meta { border-left-color: #9b51e0; }
.label { color: #607d8b; font-size: 14px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 5px; }
.ru { color: #546e7a; font-size: 17px; margin-top: 6px; }.transcription { color: #78909c; font-size: 16px; font-style: italic; margin-top: 6px; }
details summary { cursor: pointer; color: #455a64; font-weight: 700; }.muted { color: #90a4ae; } ul { margin: 7px 0; padding-left: 24px; }
"""


def make_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "B1 Greek Lexical Chunks RU-EL Recall v1",
        fields=[
            {"name": name}
            for name in [
                "ProductionCueRU", "SourceTranslationRU", "MeaningRU", "CanonicalChunk",
                "SourceSentenceHTML", "SourceSentenceEL", "SourceTranscriptionRU", "SourceAudio",
                "TransferSentenceEL", "TransferSentenceRU", "TransferTranscriptionRU",
                "TransferAudio", "LiteralGlossRU", "GrammarRU", "RegisterRU", "WordFamilyHTML",
                "EtymologyRU", "OriginRU", "MemoryHookRU", "SourceLabel", "Theme", "Priority",
            ]
        ],
        templates=[{
            "name": "Chunk Recall: Русский → Ελληνικά",
            "qfmt": """
                <div class="task">Воспроизведите греческий чанк</div>
                <div class="cue">{{ProductionCueRU}}</div>
                <div class="sentence">{{SourceTranslationRU}}</div>
                <div class="ru" style="text-align:center">Значение в этом контексте: {{MeaningRU}}</div>
            """,
            "afmt": """
                {{FrontSide}}<hr>
                <div class="chunk">{{CanonicalChunk}}</div>
                <div class="sentence">{{SourceSentenceHTML}}</div>
                <div class="audio">{{SourceAudio}}</div>
                <div class="transcription" style="text-align:center">[{{SourceTranscriptionRU}}]</div>
                <div class="box transfer"><div class="label">Проверка переноса в другой контекст</div><b>{{TransferSentenceEL}}</b><div class="audio">{{TransferAudio}}</div><div class="ru">{{TransferSentenceRU}}</div><div class="transcription">[{{TransferTranscriptionRU}}]</div></div>
                <div class="box memory"><b>Дословная опора:</b> {{LiteralGlossRU}}<br><b>Крючок:</b> {{MemoryHookRU}}</div>
                <details><summary>Грамматика, употребление и этимология</summary>
                  <div class="box meta"><b>Конструкция:</b> {{GrammarRU}}<br><b>Регистр:</b> {{RegisterRU}}<br><b>Семья:</b> {{WordFamilyHTML}}<br><b>Разбор:</b> {{EtymologyRU}}<br><b>Происхождение:</b> {{OriginRU}}</div>
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
            # The forward script normally populated this cache already, so this
            # call is local and both decks contain exactly the same analysis.
            data = analyze(client, item)
            source_audio = audio_for(item.source_sentence, media_files)
            transfer_audio = audio_for(data.transfer_sentence_el, media_files)
            priority = item.priority if item.priority != "auto" else data.recommended_priority
            fields = [
                safe(data.production_cue_ru), safe(data.source_translation_ru), safe(data.meaning_ru),
                safe(data.canonical_chunk), highlighted(item.source_sentence, data.target_surface),
                safe(item.source_sentence), safe(data.source_transcription_ru), source_audio,
                safe(data.transfer_sentence_el), safe(data.transfer_sentence_ru),
                safe(data.transfer_transcription_ru), transfer_audio, safe(data.literal_gloss_ru),
                safe(data.grammar_ru), safe(data.register_ru), list_html(data.word_family),
                safe(data.etymology_breakdown_ru), safe(data.origin_ru), safe(data.emotional_hook_ru),
                safe(item.source or "—"), safe(item.theme), safe(priority),
            ]
            note = genanki.Note(
                model=model,
                fields=fields,
                guid=genanki.guid_for("chunks-ru-el", item.source_sentence, data.canonical_chunk),
                tags=[value for value in ["b1_chunk", "active_recall", tag(item.theme), tag(priority)] if value],
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
    print(f"✅ Recall-колода создана: {OUTPUT_DECK} ({len(items)} карточек)")


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
