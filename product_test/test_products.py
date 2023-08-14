import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
import yaml
import json
from pathlib import Path
from pprint import pprint


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

        completed_jobs = statistic.split("completed_jobs:")[-1].split(" dupe_jobs:")
        self.completed_jobs = int(completed_jobs[0])

        dupe_jobs = completed_jobs[-1].split(" denied_jobs:")
        self.dupe_jobs = int(dupe_jobs[0])

        denied_jobs = dupe_jobs[-1].split(" failed_jobs:")
        self.denied_jobs = int(denied_jobs[0])

        failed_jobs = denied_jobs[-1].split(" browse-cache-hits:")
        self.failed_jobs = int(failed_jobs[0])

        time = float(failed_jobs[-1].split(":")[-1])
        hours = int(time // 3600)
        minutes = int(time % 3600 // 60)
        seconds = int(time % 3600 % 60)
        self.time = f"Hours: {hours}, minutes: {minutes}, seconds: {seconds}"


class Product:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("product_test/emits")
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"
        self.result = ResultParse(self.agent_id)

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            self.file = self.open_file()

        self.agent_name = self.file["meta"]["agent_name"]

    def generate_file(self) -> dict[list[dict]]:

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
        precent = 0
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

            precent_ = int(((product_count / self.result.emitted) * 100))
            if precent_ > precent:
                print(f" Done {precent_} %")
                precent = precent_

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

    def __init__(self, product: Product):
        self.products = product.file.get("products")
        self.agent_name = product.agent_name
        self.xproduct_names_category = ["review", "test"]#, "...", "•"]
        self.xproduct_names_category_start_end = ["+", "-"]
        self.xreview_excerpt = ["Summary", "Conclusion", "Verdict", "Fazit", "\uFEFF"]#, "•"]
        self.xreview_pros_cons = ["-", "+", "•", "None found"]
        self.path = Path(f"product_test/error/{self.agent_name}")
        self.path.mkdir(exist_ok=True)

    def test_product_name(self, xproduct_names: list[str]=[], not_xproduct_name: str=None) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names
        if not_xproduct_name:
            xproduct_names_category.remove(not_xproduct_name)
        error_name = []
        for product in self.products:
            properties = product.get("product", {}).get("properties", {})
            property = [property for property in properties if property.get("type") == "name"][0]
            name = property.get("value")

            temp_name = None
            for xname in self.xproduct_names_category_start_end:
                if name.startswith(xname) or name.endswith(xname):
                    property["error"] = f"Starts or ends '{xname}'"
                    temp_name = properties
                    break

            if not temp_name:
                for xproduct_name in xproduct_names_category:
                    if xproduct_name in name.lower():
                        property["error"] = xproduct_name
                        temp_name = properties
                        break

            if temp_name:
                error_name.append(temp_name)

        print(f"Count error product name: {len(error_name)}")
        self.save(error_name, type_err="prod_name")

    def test_product_category(self, xproduct_names: list[str]=[]) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names
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
                for xproduct_name in xproduct_names_category:
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
            property_pros = [property for property in properties if property.get("type") == "pros"]
            property_cons = [property for property in properties if property.get("type") == "cons"]
            pros = [property.get("value") for property in property_pros]
            cons = [property.get("value") for property in property_cons]

            for i, pro in enumerate(pros):
                if temp_pros_cons:
                    break
                if len(pro) < 3:
                    property_pros[i]["error"] = "< 3"
                    temp_pros_cons = properties
                    break
                if pro in cons:
                    property_pros[i]["error"] = f"Pro: '{pro}' in cons"
                    temp_pros_cons = properties
                    break
                for xreview_pros_cons in self.xreview_pros_cons:
                    if pro.startswith(xreview_pros_cons) or pro.endswith(xreview_pros_cons):
                        property_pros[i]["error"] = f"starts or ends '{xreview_pros_cons}'"
                        temp_pros_cons = properties
                        break

                for i, con in enumerate(cons):
                    if temp_pros_cons:
                        break
                    if len(con) < 3:
                        temp_pros_cons = properties
                        break
                    if con in pros:
                        property_cons[i]["error"] = f"Con: '{con}' in pros"
                        temp_pros_cons = properties
                        break
                    for xreview_pros_cons in self.xreview_pros_cons:
                        if con.startswith(xreview_pros_cons) or con.endswith(xreview_pros_cons):
                            property_cons[i]["error"] = f"starts or ends '{xreview_pros_cons}'"
                            temp_pros_cons = properties
                            break

            if temp_pros_cons:
                error_pros_cons.append(temp_pros_cons)

        print(f"Count error review pros_cons: {len(error_pros_cons)}")
        self.save(error_pros_cons, type_err="rev_pros_cons")

    def test_review_conclusion(self, xreview_conclusion: list[str] = []) -> None:
        xreview_conclusions = self.xreview_excerpt + xreview_conclusion
        error_conclusion = []
        for product in self.products:
            properties = product.get("review", {}).get("properties", {})
            property = [property for property in properties if property.get("type") == "conclusion"]

            if property:
                property = property[0]
                conclusion = property.get("value")
            else:
                continue

            for xreview_conclusion in xreview_conclusions:
                if xreview_conclusion in conclusion:
                    property["error"] = xreview_conclusion
                    error_conclusion.append(properties)
                    break

        print(f"Count error review conclusion: {len(error_conclusion)}")
        self.save(error_conclusion, type_err="rev_conclusion")

    def test_review_excerpt(self, xreview_excerpt: list[str] = [], len_chank: int = 50) -> None:
        xreview_excerpts = self.xreview_excerpt + xreview_excerpt
        error_excerpt = []
        for product in self.products:
            properties = product.get("review", {}).get("properties", {})
            conclusion = [property.get("value") for property in properties if property.get("type") == "conclusion"]
            summary = [property.get("value") for property in properties if property.get("type") == "summary"]
            property = [property for property in properties if property.get("type") == "excerpt"]

            if property:
                property = property[0]
                excerpt = property.get("value")
            else:
                properties.append({"error": "No excerpt"})
                error_excerpt.append(properties)
                continue

            if summary:
                summary = summary[0]
                chank_count = len(summary) // len_chank
                summary_list = []
                for i in range(chank_count):
                    summ = summary[len_chank * i:len_chank * ( i + 1)]
                    summary_list.append(summ)

                for element in summary_list:
                    if element in excerpt:
                        property["error"] = f"This element in excerpt: '{element}'"
                        error_excerpt.append(properties)
                        break

            for xreview_excerpt in xreview_excerpts:
                if xreview_excerpt in excerpt:
                    property["error"] = xreview_excerpt
                    error_excerpt.append(properties)
                    break

        print(f"Count error review excerpt: {len(error_excerpt)}")
        self.save(error_excerpt, type_err="rev_excerpt")

    def save(self, file: dict, type_err: str) -> None:
        file_path = self.path / f"{self.agent_name}-{type_err}.json"
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2)
