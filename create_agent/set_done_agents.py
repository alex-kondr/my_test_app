from datetime import datetime, date
from pathlib import Path
import shutil
import logging
from zoneinfo import ZoneInfo
import sys
import os
import subprocess

from sqlalchemy import select


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test import functions
from models import AgentModel, DBSession, Status


class ColoredFormatter(logging.Formatter):
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"

    COLORS = {
        'DEBUG': BLUE,
        'INFO': GREEN,
        'WARNING': YELLOW,
        'ERROR': RED,
        'CRITICAL': RED + BOLD,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        # Format the message first
        message = super().format(record)
        # Apply color to the whole line or just levelname. Here applying to the whole line for visibility.
        return f"{log_color}{message}{self.RESET}"


logger = logging.getLogger("ProductTestMulti")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = ColoredFormatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
# Перевизначаємо конвертер часу для цього форматера на Київський часовий пояс
formatter.converter = lambda timestamp: datetime.fromtimestamp(
    timestamp,
    tz=ZoneInfo("Europe/Kyiv")
).timetuple()
handler.setFormatter(formatter)
logger.addHandler(handler)


def move_remote_file_to_done(file_name_input: str):
    REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
    REMOTE_DIR = "test"

    """
    Підключається по SSH, створює папку test/done (якщо її немає)
    та переміщує туди файли .py, .txt та .pyc із папки test.
    """
    py_file_name = f"{file_name_input}.py"
    txt_file_name = f"{file_name_input}.txt"
    pyc_file_name = f"{file_name_input}.pyc"

    done_dir = f"{REMOTE_DIR}/done"

    # Формуємо bash-команду для перевірки та переміщення кожного файлу
    remote_command = (
        f"mkdir -p {done_dir} && "
        # 1. Переміщення .py файлу
        f"if [ -f {REMOTE_DIR}/{py_file_name} ]; then "
        f"  mv {REMOTE_DIR}/{py_file_name} {done_dir}/{py_file_name} && "
        f"  echo 'Успішно переміщено: {REMOTE_DIR}/{py_file_name} -> {done_dir}/{py_file_name}'; "
        f"else "
        f"  echo 'Попередження: файл {REMOTE_DIR}/{py_file_name} не знайдено.'; "
        f"fi; "
        # 2. Переміщення .txt файлу
        f"if [ -f {REMOTE_DIR}/{txt_file_name} ]; then "
        f"  mv {REMOTE_DIR}/{txt_file_name} {done_dir}/{txt_file_name} && "
        f"  echo 'Успішно переміщено: {REMOTE_DIR}/{txt_file_name} -> {done_dir}/{txt_file_name}'; "
        f"else "
        f"  echo 'Попередження: файл {REMOTE_DIR}/{txt_file_name} не знайдено.'; "
        f"fi; "
        # 3. Переміщення .pyс файлу
        f"if [ -f {REMOTE_DIR}/{pyc_file_name} ]; then "
        f"  mv {REMOTE_DIR}/{pyc_file_name} {done_dir}/{pyc_file_name} && "
        f"  echo 'Успішно переміщено: {REMOTE_DIR}/{pyc_file_name} -> {done_dir}/{pyc_file_name}'; "
        f"else "
        f"  echo 'Попередження: файл {REMOTE_DIR}/{pyc_file_name} не знайдено.'; "
        f"fi"
    )

    print(f"Підключення до {REMOTE_HOST} для переміщення файлів для '{file_name_input}' у папку done...")

    try:
        process = subprocess.run(
            ["ssh", REMOTE_HOST, remote_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=10
        )

        # Виводимо лог з сервера
        if process.stdout:
            print(process.stdout.strip())

        if process.returncode != 0:
            if process.stderr:
                print(f"Помилка SSH/сервера:\n{process.stderr.strip()}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("Помилка: Перевищено час очікування підключення по SSH.")
        return False
    except Exception as e:
        print(f"Виникла непередбачувана помилка: {e}")
        return False


def move_agent_folder(agent: AgentModel):
    date_now = datetime.now(tz=ZoneInfo("Europe/Kyiv"))
    agent_done_path = Path(f"{date_now.year}/{date_now.strftime("%Y-%m")}")
    agent_done_path.mkdir(parents=True, exist_ok=True)

    if agent.bb:
        agent_path = Path(f"{agent.source_name} (BB)")
        move_remote_file_to_done(agent.source_name)
    else:
        agent_path = Path(agent.source_name)

    if agent_path.exists():
        shutil.move(agent_path, agent_done_path / agent_path.name)
        logger.info(f"Moved {agent_path} -> {agent_done_path / agent_path.name}")
    else:
        logger.warning(f"{agent_path} not found")


def get_done_agents():
    with DBSession() as db:
        stmt = select(AgentModel).where(AgentModel.status == Status.accepted)
        agents = db.scalars(stmt).all()
        logger.info(f"Found {len(agents)} agents done")
        today = date.today()
        for agent in agents:
            try:
                functions.post_edit_page_agent(agent)
                agent.status = Status.done
                agent.end_date = today
                move_agent_folder(agent)
                db.commit()
                logger.info(f"{agent.source_name} set done")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to process {agent.source_name}: {e}", exc_info=True)


if __name__ == "__main__":
    get_done_agents()
