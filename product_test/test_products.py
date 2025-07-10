import yaml
import json
from pathlib import Path
# from concurrent.futures import ProcessPoolExecutor
# from multiprocessing import cpu_count

from product_test.functions import load_file, is_include


# CPU_COUNT = cpu_count()
# EXECUTOR = ProcessPoolExecutor(CPU_COUNT)


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
        content = load_file(agent_id=self.agent_id, type_file="log", size=400, decode=True)
        content = content.split("\n")

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
        self.emits_dir.mkdir(exist_ok=True)
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"
        self.result = ResultParse(self.agent_id)

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            self.file = self.open_file()

        self.agent_name = self.file["meta"]["agent_name"]

    def generate_file(self) -> dict[list[dict]]:
        content = load_file(agent_id=self.agent_id, type_file="yaml")
        content = yaml.load_all(content, Loader=yaml.FullLoader)

        file = {"products": []}
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
            json.dump(file, fd, indent=2, ensure_ascii=False)


class TestProduct:

    def __init__(self, product: Product):
        Path("product_test/error").mkdir(exist_ok=True)
        self.products = product.file.get("products")
        self.agent_name = product.agent_name
        self.xproduct_names_category = ["review", "test", u"\uFEFF", u"\ufeff", "...", "•", "cable", "análise", "u000", u"&amp", "обзор", "тест", "recensione", "Ã", "¼", "hírek"]
        self.xproduct_names_category_start_end = [] # ["-", "+"]
        self.xreview_title = ["\uFEFF", "\ufeff", u"U000", u"&amp"]
        self.xreview_excerpt = ["Conclusion", "Verdict", u"\uFEFF", u"\ufeff", "Summary", "Fazit", "href=", "U000", u"&amp", "Les plus", "Les moins", "Résumé", "►", "Выводы", "Slutsats", "CONTRO", "Závěr", "Ã", "¼"] #, "•"
        self.xreview_pros_cons = ["–", "-", "+", "•", "►", "none found", "null", 'n/a', 'n\\a', u"U000", u"&amp", "etc.", "Ã", "¼"]# 'na', 'no',]
        self.path = Path(f"product_test/error/{self.agent_name}")
        self.path.mkdir(exist_ok=True)
        self.product = None
        self.error_name = []
        self.error_category = []
        self.error_sku = []
        self.error_id_manufacturer = []
        self.error_ean = []
        self.error_title = []
        self.error_date = []
        self.error_grade = []
        self.error_author = []
        self.error_award = []
        self.error_pros_cons = []
        self.error_conclusion = []
        self.error_excerpt = []

    def run(self, xproduct_names=[], not_xproduct_name=None, len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[]):
        for self.product in self.products:
            self.test_product_name(xproduct_names=xproduct_names, len_name=len_name, not_xproduct_name=not_xproduct_name)
            self.test_product_category(xproduct_names)
            self.test_product_sku()
            self.test_product_id_manufacturer()
            self.test_product_ean_gtin()
            self.test_review_title(xreview_title)
            self.test_review_date()
            self.test_review_grade()
            self.test_review_author()
            self.test_review_award()
            self.test_review_pros_cons()
            self.test_review_conclusion(xreview_conclusion)
            self.test_review_excerpt(xreview_excerpt, len_chank=100, len_excerpt=3, not_xrev_excerpt=not_xproduct_name)

        # EXECUTOR.shutdown()

        print(f"Count error product name: {len(self.error_name)}")
        self.save(self.error_name, type_err="prod_name")

        print(f"Count error product category: {len(self.error_category)}")
        self.save(self.error_category, type_err="prod_category")

        print(f"Count error product sku: {len(self.error_sku)}")
        self.save(self.error_sku, type_err="prod_sku")

        print(f"Count error product id.manufacturer: {len(self.error_id_manufacturer)}")
        self.save(self.error_id_manufacturer, type_err="prod_id_manufacturer")

        print(f"Count error product ean: {len(self.error_ean)}")
        self.save(self.error_ean, type_err="prod_ean")

        print(f"Count error review title: {len(self.error_title)}")
        self.save(self.error_title, type_err="rev_title")

        print(f"Count error review date: {len(self.error_date)}")
        self.save(self.error_date, type_err="rev_date")

        print(f"Count error review grades: {len(self.error_grade)}")
        self.save(self.error_grade, type_err="rev_grades")

        print(f"Count error review author: {len(self.error_author)}")
        self.save(self.error_author, type_err="rev_author")

        print(f"Count error review award: {len(self.error_award)}")
        self.save(self.error_award, type_err="rev_award")

        print(f"Count error review pros_cons: {len(self.error_pros_cons)}")
        self.save(self.error_pros_cons, type_err="rev_pros_cons")

        print(f"Count error review conclusion: {len(self.error_conclusion)}")
        self.save(self.error_conclusion, type_err="rev_conclusion")

        print(f"Count error review excerpt: {len(self.error_excerpt)}")
        self.save(self.error_excerpt, type_err="rev_excerpt")

    def test_product_name(self, xproduct_names: list[str]=[], not_xproduct_name: str = None, len_name: int = 6) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names
        if not_xproduct_name:
            xproduct_names_category.remove(not_xproduct_name)
        properties = self.product.get("product", {}).get("properties", [])
        property = [property for property in properties if property.get("type") == "name"][0]
        name = property.get("value")

        temp_name = None
        for xname in self.xproduct_names_category_start_end:
            if name.startswith(xname) or name.endswith(xname):
                property["error_start_end"] = f"Starts or ends '{xname}'"
                temp_name = properties
                break

        if len(name) < len_name:
            property["error_len"] = f"Len name < {len_name}"
            temp_name = properties

        xproduct_name = is_include(xproduct_names_category, name, lower=True)
        if xproduct_name:
            property["error_name"] = xproduct_name
            temp_name = properties

        if temp_name:
            self.error_name.append(temp_name)

    def test_product_category(self, xproduct_names: list[str]=[]) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names

        properties = self.product.get("product", {}).get("properties", [])
        category = [property.get("value") for property in properties if property.get("type") == "category"][0]

        temp_cat = None
        for xname in self.xproduct_names_category_start_end:
            if not category or category.startswith(xname) or category.endswith(xname):
                temp_cat = properties
                break

        xproduct_name = is_include(xproduct_names_category, category, lower=True)
        if xproduct_name:
            temp_cat = properties

        if temp_cat:
            self.error_category.append(properties)

    def test_product_sku(self):
        properties = self.product.get("product", {}).get("properties", [])
        sku = [property.get("value") for property in properties if property.get("type") == "id.sku"]

        if sku and len(sku[0]) < 2:
            self.error_sku.append(properties)

    def test_product_id_manufacturer(self):
        properties = self.product.get("product", {}).get("properties", [])
        id_manufacturer = [property.get("value") for property in properties if property.get("type") == "id.manufacturer"]

        if not id_manufacturer or len(id_manufacturer[0]) < 2:
            self.error_id_manufacturer.append(properties)

    def test_product_ean_gtin(self):
        properties = self.product.get("product", {}).get("properties", [])
        ean = [property.get("value") for property in properties if property.get("type") == "id.ean"]

        if ean and (len(str(ean[0])) < 11 or not str(ean[0]).isdigit()):
            self.error_ean.append(properties)

    def test_review_title(self, xreview_title: list[str]=[]) -> None:
        xreview_title = self.xreview_title + xreview_title

        properties = self.product.get("review", {}).get("properties", [])
        property = [property for property in properties if property.get("type") == "title"]

        if not property:
            return

        property = property[0]
        title = property.get("value")

        xtitle = is_include(xreview_title, title)
        if xtitle:
            property["error_name"] = xtitle
            self.error_title.append(properties)

    def test_review_date(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        date = [property for property in properties if property.get("type") == "publish_date"]

        if not date:
            self.error_date.append(properties)

    def test_review_grade(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        grades = [property for property in properties if property.get("type") == "grade"]

        if not grades:
            self.error_grade.append(properties)

    def test_review_author(self) -> None:
        properties = self.product.get("person", {}).get("properties", [])
        author = [property for property in properties if property.get("type") == "name"]

        if not author:
            properties = self.product.get("review", {}).get("properties", [])
            properties.append({"error_no_author": "No author"})
            self.error_author.append(properties)

    def test_review_award(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        award = [property for property in properties if property.get("type") == "awards"]

        if not award:
            properties = self.product.get("review", {}).get("properties", [])
            properties.append({"error_no_award": "No award"})
            self.error_award.append(properties)

    def test_review_pros_cons(self) -> None:
        temp_pros_cons = None
        properties = self.product.get("review", {}).get("properties", [])
        property_pros = [property for property in properties if property.get("type") == "pros"]
        property_cons = [property for property in properties if property.get("type") == "cons"]
        pros = [property.get("value") for property in property_pros]
        cons = [property.get("value") for property in property_cons]

        for i, pro in enumerate(pros):
            if pro and len(pro) < 2:
                property_pros[i]["error_len"] = "< 2"
                temp_pros_cons = properties
            if pro in cons:
                property_pros[i]["error_in_con"] = f"Pro: '{pro}' in cons"
                temp_pros_cons = properties
            for xreview_pros_cons in self.xreview_pros_cons:
                if pro and (pro.lower().startswith(xreview_pros_cons) or pro.lower().endswith(xreview_pros_cons)):
                    property_pros[i]["error_start_end"] = f"starts or ends '{xreview_pros_cons}'"
                    temp_pros_cons = properties

        for i, con in enumerate(cons):
            if con and len(con) < 3:
                property_cons[i]["error_len"] = "< 3"
                temp_pros_cons = properties
            if con in pros:
                property_cons[i]["error_in_pro"] = f"Con: '{con}' in pros"
                temp_pros_cons = properties
            for xreview_pros_cons in self.xreview_pros_cons:
                if con and (con.lower().startswith(xreview_pros_cons) or con.lower().endswith(xreview_pros_cons)):
                    property_cons[i]["error_start_end"] = f"starts or ends '{xreview_pros_cons}'"
                    temp_pros_cons = properties

        if temp_pros_cons:
            self.error_pros_cons.append(temp_pros_cons)

    def test_review_conclusion(self, xreview_conclusion: list[str] = []) -> None:
        xreview_conclusions = self.xreview_excerpt + xreview_conclusion

        properties = self.product.get("review", {}).get("properties", [])
        property = [property for property in properties if property.get("type") == "conclusion"]

        if not property:
            return

        property = property[0]
        conclusion = property.get("value")

        xreview_conclusion = is_include(xreview_conclusions, conclusion)
        if xreview_conclusion:
            property["error_name"] = xreview_conclusion
            self.error_conclusion.append(properties)

    def test_review_excerpt(self, xreview_excerpt: list[str] = [], len_chank: int = 100, len_excerpt: int = 10, not_xrev_excerpt: str|None = None) -> None:
        xreview_excerpts = self.xreview_excerpt + xreview_excerpt
        if not_xrev_excerpt:
            xreview_excerpts.remove(not_xrev_excerpt)

        properties = self.product.get("review", {}).get("properties", [])
        conclusion = [property.get("value") for property in properties if property.get("type") == "conclusion"]
        summary = [property.get("value") for property in properties if property.get("type") == "summary"]
        property = [property for property in properties if property.get("type") == "excerpt"]

        if not property:
            properties.append({"error_no": "No excerpt"})
            self.error_excerpt.append(properties)
            return

        property = property[0]
        excerpt = property.get("value")

        if summary:
            summary = summary[0]
            chank_count = len(summary) // len_chank
            summary_list = []
            for i in range(chank_count):
                summ = summary[len_chank * i:len_chank * ( i + 1)]
                summary_list.append(summ)

            element = is_include(summary_list, excerpt)
            if element:
                property["error_in_sum"] = f"This element in excerpt: '{element}'"
                self.error_excerpt.append(properties)

        if conclusion:
            conclusion = conclusion[0]
            chank_count = len(conclusion) // len_chank
            conclusion_list = []
            for i in range(chank_count):
                summ = conclusion[len_chank * i:len_chank * ( i + 1)]
                conclusion_list.append(summ)

            element = is_include(conclusion_list, excerpt)
            if element:
                property["error_in_con"] = f"This element in excerpt: '{element}'"
                self.error_excerpt.append(properties)

        if len(excerpt) < len_excerpt:
            property["error_len"] = f"Len excerpt < {len_excerpt}"
            self.error_excerpt.append(properties)

        xreview_excerpt = is_include(xreview_excerpts, excerpt)
        if xreview_excerpt:
            property["error_name"] = xreview_excerpt
            self.error_excerpt.append(properties)

    def save(self, file: list, type_err: str) -> None:
        file_path = self.path / f"{type_err}.json"
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2, ensure_ascii=False)
