import os
import subprocess
import shutil
from datetime import datetime

# === НАСТРОЙКИ ===
# Замени названия на свои, если твои файлы называются иначе!
FORWARD_SCRIPT = "anki_etymology_el_rus.py"  # Скрипт Греческий -> Русский
RECALL_SCRIPT = "anki_etymology_recall_rus_el.py"      # Скрипт Русский -> Греческий

INPUT_FILE = "greek_text.txt"
ARCHIVE_DIR = "input_words_archive"

def check_files():
    """Проверяем, существуют ли нужные файлы"""
    missing = []
    for f in [FORWARD_SCRIPT, RECALL_SCRIPT, INPUT_FILE]:
        if not os.path.exists(f):
            missing.append(f)
    return missing

def archive_and_clear_input():
    """Архивируем и очищаем файл после того, как ОБА скрипта отработали"""
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    archive_path = os.path.join(ARCHIVE_DIR, f"batch_{timestamp}.txt")
    
    # Копируем файл в архив
    shutil.copy2(INPUT_FILE, archive_path)
    print(f"📁 Исходный текст сохранен в архив: {archive_path}")
    
    # Очищаем исходный файл
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write("")
    print("🧹 Файл greek_text.txt очищен и готов к новой партии слов!\n")

def run_script(script_name, description):
    """Запускает скрипт и выводит его статус"""
    print(f"\n{'='*50}")
    print(f"🚀 ЗАПУСК: {description} ({script_name})")
    print(f"{'='*50}\n")
    
    try:
        # Запускаем скрипт так же, как если бы это делали из терминала
        result = subprocess.run(["python", script_name], check=True)
        print(f"\n✅ УСПЕШНО: {description} завершен.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ОШИБКА: Скрипт {script_name} упал с ошибкой. Код: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ ОШИБКА: Не удалось вызвать 'python'. Проверь переменные среды.")
        return False

def main():
    print("🌟 Старт автоматической генерации колод Anki 🌟")
    
    # 1. Проверка файлов
    missing_files = check_files()
    if missing_files:
        print(f"⚠️ Ошибка! Не найдены файлы: {', '.join(missing_files)}")
        print("Проверь названия файлов в настройках скрипта build_decks.py")
        return

    # 2. Проверка, есть ли текст для обработки
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            print(f"ℹ️ Файл {INPUT_FILE} пуст. Добавь туда греческие предложения перед запуском.")
            return

    # 3. Поочередный запуск генераторов
    success_forward = run_script(FORWARD_SCRIPT, "Генерация колоды [Греческий -> Русский]")
    
    if success_forward:
        success_recall = run_script(RECALL_SCRIPT, "Генерация колоды [Русский -> Греческий (Recall)]")
        
        # 4. Если оба отработали успешно — архивируем текст
        if success_recall:
            print(f"\n{'='*50}")
            print("🎉 ВСЕ КОЛОДЫ УСПЕШНО СГЕНЕРИРОВАНЫ! 🎉")
            print(f"{'='*50}\n")
            archive_and_clear_input()
        else:
            print("\n⚠️ Внимание: Recall-скрипт выдал ошибку. Файл greek_text.txt НЕ очищен.")
    else:
        print("\n⚠️ Внимание: Основной скрипт выдал ошибку. Выполнение прервано.")

if __name__ == "__main__":
    main()