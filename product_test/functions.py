import os
from typing import List
import sys

from dotenv import load_dotenv
from tqdm import tqdm
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from requests_html import HTMLSession


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

urllib3.disable_warnings()
load_dotenv()


def load_file(agent_id: int, type_file: str = "yaml", size: int|str = "", decode: bool = False) -> str | bytes:
    """
    type_file: "yaml", "log"
    """
    action = {
        "log": "looksession",
        "yaml": "yaml"
    }
    url = f"https://prunesearch.com/manage?action={action[type_file]}&agent_id={agent_id}&lastbytes={size}"
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


def get_old_agent(agent_id: int) -> List[str]:
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
    return response.html
    # agent_code = response.html.find("textarea", clean=True, first=True).full_text.split('\n')
    # agent_name = response.html.xpath("//body/b/text()")[0]
    # return dict(agent_code=agent_code, agent_name=agent_name)
    # return agent_code
    # with open("agent_test.py", "w", encoding="utf-8") as file:
    #     file.writelines(strings)
# get_old_agent(20182)


def get_agent_name(html):
    return html.xpath("//body/b/text()")[0]


def get_agent_code(html):
    return html.find("textarea", clean=True, first=True).full_text.split('\n')


def get_source_name(agent_id):
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
    return response.html.xpath('//input[@name="source_name"]/@value')[0]