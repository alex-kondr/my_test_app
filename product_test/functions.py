import os
from typing import List, Optional
import sys
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from tqdm import tqdm
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from requests_html import HTMLSession

from models import AgentModel


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

urllib3.disable_warnings()
load_dotenv()


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
        message = super().format(record)
        return f"{log_color}{message}{self.RESET}"


logger = logging.getLogger("LogTest")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


def load_file(agent_id: int, type_file: str = "yaml", size: int|str = "", decode: bool = False, session_id: int = 0) -> str | bytes:
    """
    type_file: "yaml", "log"
    """
    action = {
        "log": "looksession",
        "yaml": "yaml"
    }
    url = f"https://prunesearch.com/manage?action={action[type_file]}&agent_id={agent_id}&lastbytes={size}"
    if session_id:
        url += f"&session_id={session_id}"

    response = requests.get(
        url,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        ),
        stream=True
    )

    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024  # 1 MB
    content = bytearray()

    with tqdm(total=total_size, unit='iB', unit_scale=True, unit_divisor=1024, desc=f"Downloading {type_file}") as t:
        for data in response.iter_content(block_size):
            t.update(len(data))
            content.extend(data)

    return content.decode("utf-8") if decode else bytes(content)


def is_include(xnames: list = [], text: str = "", lower: bool = False) -> str|None:
    for xname in xnames:
        if lower:
            if xname.lower() in text.lower():
                return xname
        else:
            if xname in text:
                return xname


def get_agent_name(html):
    return html.xpath('//input[@name="name"]/@value')[0]


def get_source_name(html):
    return html.xpath('//input[@name="source_name"]/@value')[0]


def get_description(html):
    return html.xpath('//textarea[@name="description"]/text()')[0]


def get_priority(html):
    return html.xpath('//input[@name="priority"]/@value')[0]


def get_group(html):
    return html.xpath('//input[@name="group"]/@value')[0]


def get_agent_code(agent_id):
    url = f"https://prunesearch.com/manage?action=agent&agent_id={agent_id}"

    session = HTMLSession()
    response = session.get(
        url,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        )
    )
    return response.html.find(
            "textarea", clean=True, first=True
        ).full_text.replace(
            "(data, context, session)",
            "(data: Response, context: dict[str, str], session: Session)"
        ).replace(
            "(context, session)",
            "(context: dict[str, str], session: Session)"
        ).split('\n')


def get_edit_page_agent(agent_id):
    url = f"https://prunesearch.com/manage?action=editagent&agent_id={agent_id}"

    session = HTMLSession()
    response = session.get(
        url,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        )
    )
    return response.html


def upload_code(agent_id, code, run: bool = True):
    url = f"https://prunesearch.com/manage?action=agent&agent_id={agent_id}"

    payload = {
        'agent_id': agent_id,
        'action': 'editagentcode',
        'code': code,
        'subaction': 'Save and run' if run else 'Save and continue editing'
    }

    response = requests.post(
        url,
        data=payload,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        ),
        stream=True
    )

    if response.status_code == 200:
        logger.info(f"Code '{payload['subaction']}' successfully")
    else:
        logger.error(f"Some error uploaded: code: {response.status_code}")


def get_end_date_agent(agent_id) -> Optional[str]:
    url = f"https://prunesearch.com/manage?action=sessions&agent_id={agent_id}"

    session = HTMLSession()
    response = session.get(
        url,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        )
    )
    date = response.html.xpath('(//td)[1]/parent::*/td[4]/text()')[0].strip()
    if date == 'None':
        error = response.html.xpath('(//td)[1]/parent::*/td[16]/text()')[0]
        emit_count = response.html.xpath('(//td)[1]/parent::*/td[8]/text()')[0]
        raise ValueError(f"{error = }\n{emit_count = }\nNot end")

    return datetime.fromisoformat(date).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")


def get_max_emit_agent(agent_id) -> Optional[str]:
    url = f"https://prunesearch.com/manage?action=sessions&agent_id={agent_id}"

    session = HTMLSession()
    response = session.get(
        url,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        )
    )
    max_emit = response.html.xpath('//td/parent::tr[not(td[contains(., "autorun")])]/td[8]/text()')
    if max_emit:
        return int(max_emit[0])
    else:
        return 0


def post_edit_page_agent(agent: AgentModel):
    if agent.bb:
        return

    url = f"https://prunesearch.com/manage?action=editagent&agent_id={agent.agent_id}"
    data = {
        "action": "editagent",
        "agent_id": agent.agent_id,
        "name": agent.name,
        "source_name": agent.source_name,
        "description": agent.description,
        "state_id": "3" if agent.done else "2",
        "priority": agent.priority,
        "group": agent.group
    }

    if agent.done:
        data["active"] = "1"

    session = HTMLSession()
    session.post(
        url,
        data=data,
        verify=False,
        auth=HTTPBasicAuth(
            username=os.getenv("USER-NAME"),
            password=os.getenv("PASS")
        ),
        stream=True
    )


