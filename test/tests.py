import requests
from requests.auth import HTTPBasicAuth
import os
from pprint import pprint
from dotenv import load_dotenv
import yaml
import json
from pathlib import Path


class TestProduct:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("test/emits")
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            self.file = self.open_file()

    def generate_file(self) -> dict[list[dict]]:

        load_dotenv()
        url = f"https://prunesearch.com/manage?action=yaml&agent_id={self.agent_id}"
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(
                username=os.getenv("USER-NAME"),
                password=os.getenv("PASS")
            )
        )

        content = yaml.load_all(response.content, Loader=yaml.FullLoader)

        file = {"products": []}
        product_num = 0
        for items in content:
            meta = items[0].get("meta")

            if meta:
                file["meta"] = meta
            else:
                product = {}
                for item in items:
                    for key, value in item.items():
                        product[key] = value

                file['products'].append(product)
                product_num += 1

            if not product_num % 100:
                print(product_num)

        print(f"{product_num=}")
        self.save_file(file)

        return file

    def open_file(self):
        with open(self.file_path, "r", encoding="utf-8") as fd:
            file = json.load(fd)
        return file

    def save_file(self, file):
        with open(self.file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2)
