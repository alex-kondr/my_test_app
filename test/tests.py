import requests
from requests.auth import HTTPBasicAuth
import os
from pprint import pprint
from dotenv import load_dotenv
import yaml
import json
from pathlib import Path


load_dotenv()


class LogProduct:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("test/logs")
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
        self.path = Path(f"test/error/log-{self.log_product.agent_id}")
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


class Product:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("test/emits")
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            self.file = self.open_file()

        self.agent_name = self.file["meta"]["agent_name"]

    def generate_file(self) -> dict[list[dict]]:

        load_dotenv()
        url = f"https://prunesearch.com/manage?action=yaml&agent_id={self.agent_id}"
        # os.system(f'curl "{url}" -k -u "{os.getenv("USER-NAME")}:{os.getenv("PASS")}" > emit.yaml')
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(
                username=os.getenv("USER-NAME"),
                password=os.getenv("PASS")
            )
        )
        file = {"products": []}
        # with open("emit.yaml", "r", encoding="utf-8") as fd:
        content = yaml.load_all(response.content, Loader=yaml.FullLoader)

        product_count = 0
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
                product_count += 1

            if not product_count % 100:
                print(product_count)

        print(f"{product_count=}")
        self.save_file(file)

        return file

    def open_file(self):
        with open(self.file_path, "r", encoding="utf-8") as fd:
            file = json.load(fd)
        return file

    def save_file(self, file):
        with open(self.file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2)


class TestProduct:

    def __init__(self, product: Product, xproduct_names: list[str]=[], xreview_excerpt: list[str] = []):
        self.products = product.file.get("products")
        self.agent_name = product.agent_name
        self.xproduct_names_category = ["review", "test"]#, "...", "•"] + xproduct_names
        self.xproduct_names_category_start_end = ["+", "-"]
        self.xreview_excerpt = ["summary", "conclusion", "fazit", "•"] + xreview_excerpt
        self.xreview_pros_cons = ["-", "+", "•", "None found"]
        self.path = Path(f"test/error/{self.agent_name}")
        self.path.mkdir(exist_ok=True)

    def test_product_name(self) -> None:
        error_name = []
        for product in self.products:
            properties = product.get("product", {}).get("properties", {})
            name = [property.get("value") for property in properties if property.get("type") == "name"][0]

            temp_name = None
            for xname in self.xproduct_names_category_start_end:
                if name.startswith(xname) or name.endswith(xname):
                    temp_name = properties
                    break

            if not temp_name:
                for xproduct_name in self.xproduct_names_category:
                    if xproduct_name in name.lower():
                        temp_name = properties
                        break

            if temp_name:
                error_name.append(temp_name)

        print(f"Count error product name: {len(error_name)}")
        self.save(error_name, type_err="prod_name")

    def test_product_category(self) -> None:
        error_category = []
        for product in self.products:
            properties = product.get("product", {}).get("properties", {})
            category = [property.get("value") for property in properties if property.get("type") == "category"][0]

            temp_cat = None
            for xname in self.xproduct_names_category_start_end:
                if not category or category.startswith(xname) or category.endswith(xname):
                    temp_cat = properties
                    continue

            if not temp_cat:
                for xproduct_name in self.xproduct_names_category:
                    if xproduct_name in category.lower():
                        temp_cat = properties
                        break

            if temp_cat:
                error_category.append(properties)

        print(f"Count error product category: {len(error_category)}")
        self.save(error_category, type_err="prod_category")

    def test_review_grade(self) -> None:
        error_grade = []
        for product in self.products:
            properties = product.get("review", {}).get("properties", {})
            grades = [property for property in properties if property.get("type") == "grade"]

            if not grades:
                error_grade.append(properties)

        print(f"Count error review grades: {len(error_grade)}")
        self.save(error_grade, type_err="rev_grades")

    def test_review_pros_cons(self) -> None:
        error_pros_cons = []
        for product in self.products:
            temp_pros_cons = None
            properties = product.get("review", {}).get("properties", {})
            pros_cons = [property.get("value") for property in properties if property.get("type") == "pros" or property.get("type") == "cons"]

            for pro_con in pros_cons:
                if temp_pros_cons:
                    break
                if len(pro_con) < 3:
                    temp_pros_cons = properties
                    break
                for xreview_pros_cons in self.xreview_pros_cons:
                    if pro_con.startswith(xreview_pros_cons) or pro_con.endswith(xreview_pros_cons):
                        temp_pros_cons = properties
                        break

            if temp_pros_cons:
                error_pros_cons.append(temp_pros_cons)

        print(f"Count error review pros_cons: {len(error_pros_cons)}")
        self.save(error_pros_cons, type_err="rev_pros_cons")

    def test_review_excerpt(self) -> None:
        error_excerpt = []
        for product in self.products:
            properties = product.get("review", {}).get("properties", {})
            excerpt = [property for property in properties if property.get("type") == "excerpt"]

            if excerpt:
                excerpt = excerpt[0]
            else:
                error_excerpt.append(properties)
                continue

            for xreview_excerpt in self.xreview_excerpt:
                if xreview_excerpt in excerpt:
                    error_excerpt.append(properties)
                    break

        print(f"Count error review excerpt: {len(error_excerpt)}")
        self.save(error_excerpt, type_err="rev_excerpt")

    def save(self, file: dict, type_err: str) -> None:
        file_path = self.path / f"{self.agent_name}-{type_err}.json"
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2)
