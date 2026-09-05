"""Build both B1 chunk decks and archive the input only after both succeed."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


FORWARD_SCRIPT = Path("anki_b1_chunks_el_rus.py")
RECALL_SCRIPT = Path("anki_b1_chunks_rus_el.py")
INPUT_FILE = Path(os.getenv("ANKI_CHUNKS_INPUT", "greek_text.txt"))
ARCHIVE_DIR = Path("input_words_archive")


def missing_files() -> list[Path]:
    return [path for path in [FORWARD_SCRIPT, RECALL_SCRIPT, INPUT_FILE] if not path.exists()]


def archive_and_clear_input() -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    archive_path = ARCHIVE_DIR / f"chunks_{timestamp}{INPUT_FILE.suffix or '.txt'}"
    shutil.copy2(INPUT_FILE, archive_path)
    INPUT_FILE.write_text("", encoding="utf-8")
    print(f"📁 Исходный материал сохранён: {archive_path}")
    print(f"🧹 Файл {INPUT_FILE} очищен и готов к новой партии чанков")
    return archive_path


def run_script(script: Path, description: str) -> bool:
    print("\n" + "=" * 58)
    print(f"🚀 {description}: {script}")
    print("=" * 58)
    try:
        subprocess.run([sys.executable, str(script)], check=True)
        print(f"✅ {description}: готово")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"❌ {script} завершился с кодом {exc.returncode}")
        return False


def main() -> int:
    missing = missing_files()
    if missing:
        print("❌ Не найдены файлы: " + ", ".join(map(str, missing)))
        return 1

    if not INPUT_FILE.read_text(encoding="utf-8").strip():
        print(f"ℹ️ Файл {INPUT_FILE} пуст. Добавь туда предложения и целевые чанки.")
        return 0

    if not run_script(FORWARD_SCRIPT, "Колода Ελληνικά → Русский"):
        print(f"⚠️ {INPUT_FILE} сохранён без изменений")
        return 1
    if not run_script(RECALL_SCRIPT, "Колода Русский → Ελληνικά"):
        print(f"⚠️ {INPUT_FILE} сохранён без изменений")
        return 1

    archive_and_clear_input()
    print("\n🎉 Обе колоды успешно созданы")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
