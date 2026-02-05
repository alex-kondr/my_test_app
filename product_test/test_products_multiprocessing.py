import yaml
import json
import logging
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from collections import defaultdict

from product_test.functions import load_file, is_include


# --- Logging Configuration with Colors ---
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
handler.setFormatter(ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(handler)
# -----------------------------------------


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

        try:
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

        except Exception as e:
            logger.error(f"Error parsing result logs: {e}")
            self.emitted = 0
            self.completed_jobs = 0
            self.dupe_jobs = 0
            self.denied_jobs = 0
            self.failed_jobs = 0
            self.time = "Error"


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

        self.agent_name = self.file["meta"]["agent_name"].strip()

    def generate_file(self) -> dict:
        logger.info(f"Loading YAML for agent {self.agent_id}...")
        content = load_file(agent_id=self.agent_id, type_file="yaml")
        content = yaml.load_all(content, Loader=yaml.FullLoader)

        file = {"products": []}
        product_count = 0
        percent = 0

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

            if self.result.emitted > 0:
                percent_ = int(((product_count / self.result.emitted) * 100))
                if percent_ > percent:
                    logger.info(f"Done {percent_} %")
                    percent = percent_

        logger.info(f"Total products processed: {product_count}")
        self.save_file(file)
        return file

    def open_file(self):
        logger.info(f"Opening existing file: {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as fd:
            file = json.load(fd)
        return file

    def save_file(self, file):
        logger.info(f"Saving file to: {self.file_path}")
        with open(self.file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2, ensure_ascii=False)


class ProductValidator:
    """
    Validates a single product. Used by worker processes.
    """
    def __init__(self, product_data):
        self.product = product_data
        self.errors = defaultdict(list)

        self.xproduct_names_category = ["review", "test", u"\uFEFF", u"\ufeff", "...", "•", "cable", "análise", "u000", u"&amp", "обзор", "тест", "recensione", "Ã", "¼", "hírek", "reseña", "inceleme"]
        self.xproduct_names_category_start_end = []
        self.xreview_title = ["\uFEFF", "\ufeff", u"U000", u"&amp"]
        self.xreview_excerpt = ["Conclusion", "Verdict", u"\uFEFF", u"\ufeff", "Summary", "Fazit", "href=", "U000", u"&amp", "Les plus", "Les moins", "Résumé", "►", "Выводы", "Slutsats", "CONTRO", "Závěr", "Ã", "¼", "PREGI", "DIFETTI"]
        self.xreview_pros_cons = ["–", "-", "+", "•", "►", "none found", 'n/a', 'n\\a', u"U000", u"&amp", "etc.", "Ã", "¼"]

    def validate(self, config):
        self.test_product_name(
            xproduct_names=config.get('xproduct_names', []),
            not_xproduct_name=config.get('not_xproduct_name'),
            len_name=config.get('len_name', 3)
        )
        self.test_product_category(config.get('xproduct_names', []))
        self.test_product_sku()
        self.test_product_id_manufacturer()
        self.test_product_ean_gtin()
        self.test_review_title(config.get('xreview_title', []))
        self.test_review_date()
        self.test_review_grade()
        self.test_review_author()
        self.test_review_award()
        self.test_review_pros_cons()
        self.test_review_conclusion(config.get('xreview_conclusion', []))
        self.test_review_excerpt(
            xreview_excerpt=config.get('xreview_excerpt', []),
            len_chank=100,
            len_excerpt=3,
            not_xrev_excerpt=config.get('not_xproduct_name')
        )
        return self.errors

    def test_product_name(self, xproduct_names: list[str]=[], not_xproduct_name: str = None, len_name: int = 6) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names
        if not_xproduct_name and not_xproduct_name in xproduct_names_category:
            xproduct_names_category.remove(not_xproduct_name)

        properties = self.product.get("product", {}).get("properties", [])
        name_props = [p for p in properties if p.get("type") == "name"]
        if not name_props:
            return

        property = name_props[0]
        name = property.get("value")
        if not name:
            return

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
            self.errors["prod_name"].append(temp_name)

    def test_product_category(self, xproduct_names: list[str]=[]) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names + [')', '(']

        properties = self.product.get("product", {}).get("properties", [])
        cat_props = [p for p in properties if p.get("type") == "category"]
        if not cat_props:
            return

        category = cat_props[0].get("value")

        temp_cat = None
        for xname in self.xproduct_names_category_start_end:
            if not category or category.startswith(xname) or category.endswith(xname):
                temp_cat = properties
                break

        if category:
            xproduct_name = is_include(xproduct_names_category, category, lower=True)
            if xproduct_name:
                temp_cat = properties

        if temp_cat:
            self.errors["prod_category"].append(properties)

    def test_product_sku(self):
        properties = self.product.get("product", {}).get("properties", [])
        sku = [property.get("value") for property in properties if property.get("type") == "id.sku"]

        if sku and len(sku[0]) < 2:
            self.errors["prod_sku"].append(properties)

    def test_product_id_manufacturer(self):
        properties = self.product.get("product", {}).get("properties", [])
        id_manufacturer = [property.get("value") for property in properties if property.get("type") == "id.manufacturer"]

        if not id_manufacturer or len(id_manufacturer[0]) < 2:
            self.errors["prod_id_manufacturer"].append(properties)

    def test_product_ean_gtin(self):
        properties = self.product.get("product", {}).get("properties", [])
        ean = [property.get("value") for property in properties if property.get("type") == "id.ean"]

        if ean and (len(str(ean[0])) < 11 or not str(ean[0]).isdigit()):
            self.errors["prod_ean"].append(properties)

    # ... (Other test methods follow similar pattern, using self.errors instead of self.error_list) ...
    # For brevity, I'm including the key logic for the rest of the methods implicitly via the Validator structure
    # You should copy the logic from the original file for test_review_* methods and adapt them to append to self.errors[key]

    def test_review_title(self, xreview_title: list[str]=[]) -> None:
        xreview_title = self.xreview_title + xreview_title
        properties = self.product.get("review", {}).get("properties", [])
        property = [property for property in properties if property.get("type") == "title"]

        if not property: return

        title = property[0].get("value")
        xtitle = is_include(xreview_title, title)
        if xtitle:
            property[0]["error_name"] = xtitle
            self.errors["rev_title"].append(properties)

    def test_review_date(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        date = [property for property in properties if property.get("type") == "publish_date"]
        if not date: self.errors["rev_date"].append(properties)

    def test_review_grade(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        grades = [property for property in properties if property.get("type") == "grade"]
        if not grades: self.errors["rev_grades"].append(properties)

    def test_review_author(self) -> None:
        properties = self.product.get("person", {}).get("properties", [])
        author = [property for property in properties if property.get("type") == "name"]
        if not author:
            properties = self.product.get("review", {}).get("properties", [])
            properties.append({"error_no_author": "No author"})
            self.errors["rev_author"].append(properties)

    def test_review_award(self) -> None:
        properties = self.product.get("review", {}).get("properties", [])
        award = [property for property in properties if property.get("type") == "awards"]
        if not award:
            properties = self.product.get("review", {}).get("properties", [])
            properties.append({"error_no_award": "No award"})
            self.errors["rev_award"].append(properties)

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
            self.errors["rev_pros_cons"].append(temp_pros_cons)

    def test_review_conclusion(self, xreview_conclusion: list[str] = []) -> None:
        xreview_conclusions = self.xreview_excerpt + xreview_conclusion
        properties = self.product.get("review", {}).get("properties", [])
        property = [property for property in properties if property.get("type") == "conclusion"]
        if not property: return
        conclusion = property[0].get("value")
        xreview_conclusion = is_include(xreview_conclusions, conclusion)
        if xreview_conclusion:
            property[0]["error_name"] = xreview_conclusion
            self.errors["rev_conclusion"].append(properties)

    def test_review_excerpt(self, xreview_excerpt: list[str] = [], len_chank: int = 100, len_excerpt: int = 10, not_xrev_excerpt: str|None = None) -> None:
        xreview_excerpts = self.xreview_excerpt + xreview_excerpt
        if not_xrev_excerpt and not_xrev_excerpt in xreview_excerpts:
            xreview_excerpts.remove(not_xrev_excerpt)

        properties = self.product.get("review", {}).get("properties", [])
        conclusion = [property.get("value") for property in properties if property.get("type") == "conclusion"]
        summary = [property.get("value") for property in properties if property.get("type") == "summary"]
        property = [property for property in properties if property.get("type") == "excerpt"]

        if not property:
            properties.append({"error_no": "No excerpt"})
            self.errors["rev_excerpt"].append(properties)
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
                self.errors["rev_excerpt"].append(properties)

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
                self.errors["rev_excerpt"].append(properties)

        if len(excerpt) < len_excerpt:
            property["error_len"] = f"Len excerpt < {len_excerpt}"
            self.errors["rev_excerpt"].append(properties)

        xreview_excerpt = is_include(xreview_excerpts, excerpt)
        if xreview_excerpt:
            property["error_name"] = xreview_excerpt
            self.errors["rev_excerpt"].append(properties)


def worker_task(args):
    """
    Worker function to process a single product.
    Must be at module level to be picklable.
    """
    product_data, config = args
    validator = ProductValidator(product_data)
    return validator.validate(config)


class TestProductMultiprocessing:
    def __init__(self, product: Product):
        Path("product_test/error").mkdir(exist_ok=True)
        self.products = product.file.get("products")
        self.agent_name = product.agent_name
        self.path = Path(f"product_test/error/{self.agent_name}")
        self.path.mkdir(exist_ok=True)

    def run(self, xproduct_names=[], not_xproduct_name=None, len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[]):
        config = {
            'xproduct_names': xproduct_names,
            'not_xproduct_name': not_xproduct_name,
            'len_name': len_name,
            'xreview_title': xreview_title,
            'xreview_conclusion': xreview_conclusion,
            'xreview_excerpt': xreview_excerpt
        }

        num_processes = cpu_count()
        logger.info(f"Starting multiprocessing with {num_processes} cores for {len(self.products)} products.")

        with Pool(num_processes) as p:
            # Prepare arguments for map
            tasks = [(prod, config) for prod in self.products]
            results = p.map(worker_task, tasks)

        # Aggregate results
        logger.info("Aggregating results...")
        aggregated_errors = defaultdict(list)
        for res in results:
            for key, val in res.items():
                aggregated_errors[key].extend(val)

        # Save results and log
        error_types = [
            ("prod_name", "product name"),
            ("prod_category", "product category"),
            ("prod_sku", "product sku"),
            ("prod_id_manufacturer", "product id.manufacturer"),
            ("prod_ean", "product ean"),
            ("rev_title", "review title"),
            ("rev_date", "review date"),
            ("rev_grades", "review grades"),
            ("rev_author", "review author"),
            ("rev_award", "review award"),
            ("rev_pros_cons", "review pros_cons"),
            ("rev_conclusion", "review conclusion"),
            ("rev_excerpt", "review excerpt"),
        ]

        for key, desc in error_types:
            errors = aggregated_errors.get(key, [])
            logger.info(f"Count error {desc}: {len(errors)}")
            self.save(errors, type_err=key)

    def save(self, file: list, type_err: str) -> None:
        file_path = self.path / f"{type_err}.json"
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2, ensure_ascii=False)
