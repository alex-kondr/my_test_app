import os
import subprocess
from uuid import uuid4
import sys


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from models import AgentModel, AgentType, DBSession


FILE_NAME_INPUT = "review.thule.com"


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
REMOTE_DIR = "test"  # Віддалена папка на сервері

def main():
    # 1. Запитуємо назву файлу у користувача
    if not FILE_NAME_INPUT:
        print("Помилка: Назва файлу не може бути порожньою.")
        return

    # Дописуємо .py до назви віддаленого файлу
    remote_file_name = f"{FILE_NAME_INPUT}.py"
    remote_full_path = f"{REMOTE_DIR}/{remote_file_name}"

    # Формуємо шлях для локальної папки
    local_dir = f"{FILE_NAME_INPUT} (BB)"

    # 2. Створюємо локальну папку, якщо її ще немає
    os.makedirs(local_dir, exist_ok=True)
    print(f"Створено/перевірено локальну папку: '{local_dir}'")

    # 3. Читаємо файл з віддаленого сервера напряму в оперативну пам'ять (без збереження на диск)
    print(f"Завантаження файлу '{remote_full_path}' у буфер...")
    try:
        scp_process = subprocess.run(
            ["ssh", REMOTE_HOST, f"cat {remote_full_path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )

        if scp_process.returncode != 0:
            print(f"Помилка: Не вдалося прочитати віддалений файл.\n{scp_process.stderr}")
            return

        file_content = scp_process.stdout.replace(
            "(data, context, session)",
            "(data: Response, context: dict[str, str], session: Session)"
        ).replace(
            "(context, session)",
            "(context: dict[str, str], session: Session)"
        )
        print("Файл успішно завантажено в оперативну пам'ять.")
    except Exception as e:
        print(f"Виникла помилка під час підключення: {e}")
        return

    # 4. Створюємо дві копії (new_ та old_) у цій папці з буфера
    try:
        new_file_path = os.path.join(local_dir, f"new_{remote_file_name}")
        old_file_path = os.path.join(local_dir, f"old_{remote_file_name}")

        # Записуємо вміст з пам'яті у файли
        with open(new_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        with open(old_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        print(f"Успішно створено копії у папці '{local_dir}':")
        print(f"   - new_{remote_file_name}")
        print(f"   - old_{remote_file_name}")

        with open(f"create_agent/upload_code_bb.txt", "r", encoding="utf-8") as f:
            content = f.read().replace("{FILE_NAME_INPUT}", FILE_NAME_INPUT)

        with open(f"{local_dir}/upload_code_bb.py", "w", encoding="utf-8") as f:
            f.write(content)

        with DBSession() as session:
            agent = AgentModel(
                agent_id=f"bb_{uuid4().hex}",
                name=FILE_NAME_INPUT,
                source_name=FILE_NAME_INPUT,
                old_code=file_content,
                agent_type=AgentType.BIG,
                bb=True
            )
            session.add(agent)
            session.commit()

    except Exception as e:
        print(f"Помилка при створенні копій файлу: {e}")

if __name__ == "__main__":
    main()