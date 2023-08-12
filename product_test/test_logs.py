from dotenv import load_dotenv
import os
from pathlib import Path
from pprint import pprint
import requests
from requests.auth import HTTPBasicAuth
import json


load_dotenv()


class ResultParse:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.result()

    def __str__(self):
        return f"""
Agent id: {self.agent_id}
Found {self.emitted} emitted objects
Completed_jobs: {self.completed_jobs}
Dupe jobs: {self.dupe_jobs}
Denied jobs: {self.denied_jobs}
Failed jobs: {self.failed_jobs}
Wasted time: {self.time}
            """

    def result(self):
        url = f"https://prunesearch.com/manage?action=looksession&agent_id={self.agent_id}&lastbytes=400"
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(
                username=os.getenv("USER-NAME"),
                password=os.getenv("PASS")
            )
        )

        content = response.content.decode("utf-8").split("\n")

        emitted = content[-4].split("Found ")[-1].split(" emitted")[0]
        self.emitted = int(emitted)

        statistic = "".join(content[-7:-5])
        print(statistic)

        completed_jobs = statistic.split("completed_jobs:")[-1].split(" dupe_jobs:")
        print(f"{completed_jobs=}")
        self.completed_jobs = int(completed_jobs[0])

        dupe_jobs = completed_jobs[-1].split(" denied_jobs:")
        print(f"{dupe_jobs}")
        self.dupe_jobs = int(dupe_jobs[0])

        denied_jobs = dupe_jobs[-1].split(" failed_jobs:")
        print(f"{denied_jobs=}")
        self.denied_jobs = int(denied_jobs[0])

        failed_jobs = denied_jobs[-1].split(" browse-cache-hits:")
        print(f"{failed_jobs=}")
        self.failed_jobs = int(failed_jobs[0])

        time = failed_jobs[-1].split(":")[-1]
        print(f"{time=}")
        hours = int(float(time) // 3600)
        minutes = int(float(time) % 3600 // 60)
        seconds = int(round(float(time) % 3600 % 60, 0))
        self.time = f"Hours: {hours}, minutes: {minutes}, seconds: {seconds}"


class LogProduct:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("product_test/logs")
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            self.file = self.open_file()

    def generate_file(self) -> list:
        print("Get logs...")
        url = f"https://prunesearch.com/manage?action=looksession&agent_id={self.agent_id}"
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(
                username=os.getenv("USER-NAME"),
                password=os.getenv("PASS")
            )
        )

        content = response.content.decode("utf-8").split("\n")
        print("Get logs complete. Saving logs...")

        self.save_file(content)
        print("Logs saved succesfull.")
        return self.open_file()

    def open_file(self):
        with open(self.file_path, "r", encoding="utf-8") as fd:
            file = json.load(fd)
        return file

    def save_file(self, file):
        with open(self.file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2)

class TestLogProduct:

    def __init__(self, log_product: LogProduct):
        self.log_product = log_product
        self.xwords = ["error "]
        self.path = Path(f"product_test/error/log-{self.log_product.agent_id}")
        self.path.mkdir(exist_ok=True)

    def test_log(self):
        error_log = []
        count_lines = 0
        for i, log_product in enumerate(self.log_product.file):
            count_lines += 1
            for xword in self.xwords:
                if log_product.startswith(xword):
                    error = [
                        self.log_product.file[i-7].split("Request GET u'")[-1].split("'&gt;")[0],
                        self.log_product.file[i-8].split("Request GET u'")[-1].split("'&gt;")[0],
                        log_product
                    ]
                    error_log.append(error)
                    break

            if not count_lines % 10000:
                print(f"{count_lines=}")

        print(f"All count logs: {len(self.log_product.file)}")
        print(f"Find error in logs: {len(error_log)}")
        self.save(error_log)

    def save(self, error_log: list):
        with open(self.path / f"log.json", "w", encoding="utf-8") as fd:
            json.dump(error_log, fd, indent=2)
