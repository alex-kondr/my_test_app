from datetime import datetime, date
from pathlib import Path
import shutil
import logging
from zoneinfo import ZoneInfo
import sys
import os


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


def move_agent_folder(agent: AgentModel):
    date_now = datetime.now()
    agent_done_path = Path(f"{date_now.year}/{date_now.strftime("%Y-%m")}")
    agent_done_path.mkdir(parents=True, exist_ok=True)

    agent_path = Path(agent.source_name)
    if not agent_path.exists():
        agent_path = Path(f"{agent.source_name} (BB)")

    if agent_path.exists():
        shutil.move(agent_path, agent_done_path / agent_path.name)
        logger.info(f"Moved {agent_path} -> {agent_done_path / agent_path.name}")
    else:
        logger.warning(f"{agent_path} not found")


def get_done_agents():
    with DBSession() as db:
        agents = db.query(AgentModel).filter_by(done=True, status=Status.qc).all()

        logger.info(f"Found {len(agents)} agents done")

        for agent in agents:
            functions.post_edit_page_agent(agent, done=True)
            agent.status = Status.done
            agent.end_date = date.today()
            move_agent_folder(agent)
            logger.info(f"{agent.source_name} set done")

        db.commit()


get_done_agents()
