from dotenv import load_dotenv
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib3


urllib3.disable_warnings()
load_dotenv()


def load_file(agent_id: int, type_file: str = "yaml", size: int|str = "", decode: bool = False) -> str:
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
        )
    )

    return response.content.decode("utf-8") if decode else response.content


def is_include(xnames: list = [], text: str = "", lower: bool = False) -> str|None:
    text_ = text.lower() if lower else text

    for xname in xnames:
        if xname.lower() in text_:
            return xname