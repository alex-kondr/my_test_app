import yaml
import json
import logging
import sys
from pathlib import Path
import time
import re
from multiprocessing import Pool, cpu_count
from collections import defaultdict
from tqdm import tqdm
import os
import difflib

from product_test.functions import load_file, is_include


def is_include(xnames: list = [], text: str = "", lower: bool = False) -> str|None:
    if not xnames or not text:
        return None
    # Build a regex pattern: word1|word2|word3 for faster searching
    # We escape to treat special characters literally
    pattern = '|'.join(re.escape(xname) for xname in xnames)
    flags = re.IGNORECASE if lower else 0
    match = re.search(pattern, text, flags)
    return match.group(0) if match else None

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


def calculate_code_change(old_file_path: Path, new_file_path: Path) -> tuple[int, int, float, float] | None:
    """
    Compares two files and calculates the percentage of change.
    Returns a tuple of (added_lines, deleted_lines, percentage_with_whitespace, percentage_without_whitespace), or None on error.
    Added/deleted lines are counted from a whitespace-sensitive comparison.
    """
    try:
        with open(old_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            old_lines = f.readlines()
        with open(new_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            new_lines = f.readlines()
    except FileNotFoundError as e:
        logger.error(f"File not found during code change calculation: {e}")
        return None

    # --- Calculation with whitespace (considers indentation and trailing spaces) ---
    differ_ws = difflib.Differ()
    diff_ws = list(differ_ws.compare(old_lines, new_lines))
    added_lines = len([line for line in diff_ws if line.startswith('+ ')])
    deleted_lines = len([line for line in diff_ws if line.startswith('- ')])

    total_lines_old = len(old_lines)
    if total_lines_old == 0:
        percentage_ws = 100.0 if added_lines > 0 else 0.0
    else:
        percentage_ws = (added_lines + deleted_lines) / total_lines_old * 100

    # --- Calculation without whitespace (ignores leading/trailing spaces) ---
    old_lines_stripped = [line.strip() for line in old_lines]
    new_lines_stripped = [line.strip() for line in new_lines]

    differ_no_ws = difflib.Differ()
    diff_no_ws = list(differ_no_ws.compare(old_lines_stripped, new_lines_stripped))
    added_lines_no_ws = len([line for line in diff_no_ws if line.startswith('+ ')])
    deleted_lines_no_ws = len([line for line in diff_no_ws if line.startswith('- ')])

    if total_lines_old == 0:
        percentage_no_ws = 100.0 if added_lines_no_ws > 0 else 0.0
    else:
        # The number of changed lines ignoring whitespace, as a percentage of original total lines.
        percentage_no_ws = (added_lines_no_ws + deleted_lines_no_ws) / total_lines_old * 100

    return added_lines, deleted_lines, percentage_ws, percentage_no_ws


def check_code_changes(root_dir: str = None):
    """
    Analyzes the specified directory for 'old_*' and 'new_*' file pairs and logs code changes.
    If root_dir is not provided, it will search from the project's root directory.
    """
    root_path = Path(root_dir).parent if root_dir else Path(__file__).parent
    logger.info("-" * 40)
    logger.info(f"Analyzing directory for code changes: {root_path.resolve()}")
    found_pairs = False
    for dirpath, _, filenames in os.walk(root_path):
        old_files = [f for f in filenames if f.startswith('old_')]
        for old_file_name in old_files:
            new_file_name = 'new_' + old_file_name[len('old_'):]
            if new_file_name in filenames:
                found_pairs = True
                result = calculate_code_change(Path(dirpath) / old_file_name, Path(dirpath) / new_file_name)
                if result:
                    added, deleted, percentage_ws, percentage_no_ws = result
                    relative_path = Path(dirpath).relative_to(root_path)
                    logger.info(f"Comparison for '{old_file_name[4:]}' in './{relative_path}':")
                    logger.info(f"  - Added: {added}, Deleted: {deleted} (literal lines)")
                    logger.info(f"  - Change (with whitespace): {percentage_ws:.2f}%")
                    logger.info(f"  - Change (ignoring whitespace): {percentage_no_ws:.2f}%")
    if not found_pairs:
        logger.warning("No 'old_*' and 'new_*' file pairs found to compare.")
    logger.info("-" * 40)


def process_yaml_item(items):
    """
    Processes a single item from the YAML file.
    Must be a top-level function to be picklable.
    """
    try:
        if not isinstance(items, list) or not items:
            logger.warning(f"Skipping invalid YAML item (not a list or empty): {str(items)[:200]}")
            return {}
        meta = items[0].get("meta")
        if meta:
            return {"meta": meta}
        else:
            product = {}
            for item in items:
                for key, value in item.items():
                    product[key] = value
            return {"product": product}
    except Exception as e:
        logger.error(f"Error processing YAML item: {e}. Item: {str(items)[:200]}")
        return {}


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

        try:
            def find_stat(pattern, text):
                match = re.search(pattern, text)
                return int(match.group(1)) if match else 0

            self.emitted = find_stat(r"Found (\d+) emitted", content)
            self.completed_jobs = find_stat(r"completed_jobs:(\d+)", content)
            self.dupe_jobs = find_stat(r"dupe_jobs:(\d+)", content)
            self.denied_jobs = find_stat(r"denied_jobs:(\d+)", content)
            self.failed_jobs = find_stat(r"failed_jobs:(\d+)", content)

            time_in_seconds = 0.0
            # Ця логіка з регулярними виразами замінює крихкий парсинг часу на основі split.
            # Спочатку вона намагається знайти число після останнього двокрапки, що йде за "browse-cache-hits:".
            time_match = re.search(r"browse-cache-hits:.*:([\d\.]+)", content)
            if not time_match:
                # Якщо це не вдається, вона шукає число безпосередньо після "browse-cache-hits:".
                time_match = re.search(r"browse-cache-hits:([\d\.]+)", content)

            if time_match:
                try:
                    time_in_seconds = float(time_match.group(1))
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse time value from log: '{time_match.group(1)}'")

            hours = int(time_in_seconds // 3600)
            minutes = int(time_in_seconds % 3600 // 60)
            seconds = int(time_in_seconds % 3600 % 60)
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
        total_start_time = time.time()
        logger.info(f"Loading YAML for agent {self.agent_id}...")

        load_start_time = time.time()
        content = load_file(agent_id=self.agent_id, type_file="yaml")
        load_end_time = time.time()
        logger.info(f"YAML loading took: {load_end_time - load_start_time:.2f} seconds")

        processing_start_time = time.time()
        logger.info("Parsing YAML and processing with multiprocessing...")

        content_list = list(yaml.load_all(content, Loader=yaml.FullLoader))

        file = {"products": []}
        num_processes = cpu_count()

        # Calculate a reasonable chunksize to improve performance
        chunksize = max(1, len(content_list) // (num_processes * 4))
        logger.info(f"Using chunksize: {chunksize} for YAML parsing.")

        with Pool(num_processes) as p:
            results_iterator = p.imap_unordered(process_yaml_item, content_list, chunksize=chunksize)

            # Wrap the iterator with tqdm for a progress bar
            for res in tqdm(results_iterator, total=len(content_list), desc=f"Parsing YAML (chunksize={chunksize})"):
                if res.get("meta"):
                    file["meta"] = res["meta"]
                elif res.get("product"):
                    file['products'].append(res["product"])

        processing_end_time = time.time()
        logger.info(f"YAML processing took: {processing_end_time - processing_start_time:.2f} seconds")

        logger.info(f"Total products processed: {len(file['products'])}")
        save_start_time = time.time()
        self.save_file(file)
        save_end_time = time.time()
        logger.info(f"Saving to JSON took: {save_end_time - save_start_time:.2f} seconds")

        total_end_time = time.time()
        logger.info(f"Total generate_file time: {total_end_time - total_start_time:.2f} seconds")
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
        self.original_product = product_data
        self.product_map = self._structure_product(product_data)
        self.errors = defaultdict(list)

        self.xproduct_names_category = ["review", "test", u"\uFEFF", u"\ufeff", "...", "•", "cable", "análise", "u000", u"&amp", "обзор", "тест", "recensione", "Ã", "¼", "hírek", "reseña", "inceleme"]
        self.xproduct_names_category_start_end = []
        self.xreview_title = ["\uFEFF", "\ufeff", u"U000", u"&amp"]
        self.xreview_excerpt = ["Conclusion", "Verdict", u"\uFEFF", u"\ufeff", "Summary", "Fazit", "href=", "U000", u"&amp", "Les plus", "Les moins", "Résumé", "►", "Выводы", "Slutsats", "CONTRO", "Závěr", "Ã", "¼", "PREGI", "DIFETTI"]
        self.xreview_pros_cons = ["–", "-", "+", "•", "►", "none found", 'n/a', 'n\\a', u"U000", u"&amp", "etc.", "Ã", "¼"]
        # Compile regex for pros/cons check to improve performance
        pros_cons_pattern_parts = [re.escape(x) for x in self.xreview_pros_cons]
        self.pros_cons_regex = re.compile(f"^({'|'.join(pros_cons_pattern_parts)})|({'|'.join(pros_cons_pattern_parts)})$", re.IGNORECASE)

    def _structure_product(self, product_data):
        structured = defaultdict(list)
        for section_key, section_value in product_data.items():
            if isinstance(section_value, dict) and 'properties' in section_value:
                for prop in section_value.get('properties', []):
                    prop_type = prop.get('type')
                    if prop_type:
                        structured_key = f"{section_key}.{prop_type}"
                        structured[structured_key].append(prop)
        return structured

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

        name_props = self.product_map.get("product.name")
        if not name_props:
            return

        property = name_props[0]
        name = property.get("value", "")
        if not name:
            return

        temp_name = None
        for xname in self.xproduct_names_category_start_end:
            if name.startswith(xname) or name.endswith(xname):
                property["error_start_end"] = f"Starts or ends '{xname}'"
                temp_name = True
                break

        if len(name) < len_name:
            property["error_len"] = f"Len name < {len_name}"
            temp_name = True

        xproduct_name = is_include(xproduct_names_category, name, lower=True)
        if xproduct_name:
            property["error_name"] = xproduct_name
            temp_name = True

        if temp_name:
            self.errors["prod_name"].append(self.original_product.get("product", {}).get("properties", []))

    def test_product_category(self, xproduct_names: list[str]=[]) -> None:
        xproduct_names_category = self.xproduct_names_category + xproduct_names + [')', '(']

        properties = self.original_product.get("product", {}).get("properties", [])
        cat_props = self.product_map.get("product.category")
        if not cat_props:
            return

        category = cat_props[0].get("value")

        temp_cat = None
        for xname in self.xproduct_names_category_start_end:
            if not category or category.startswith(xname) or category.endswith(xname):
                temp_cat = True
                break

        if category:
            xproduct_name = is_include(xproduct_names_category, category, lower=True)
            if xproduct_name:
                temp_cat = properties

        if temp_cat:
            self.errors["prod_category"].append(properties)

    def test_product_sku(self):
        sku_props = self.product_map.get("product.id.sku")

        if sku_props:
            sku_value = sku_props[0].get("value")
            if sku_value and len(sku_value) < 2:
                self.errors["prod_sku"].append(self.original_product.get("product", {}).get("properties", []))

    def test_product_id_manufacturer(self):
        id_manufacturer_props = self.product_map.get("product.id.manufacturer")

        if not id_manufacturer_props or not id_manufacturer_props[0].get("value") or len(id_manufacturer_props[0].get("value")) < 2:
            self.errors["prod_id_manufacturer"].append(self.original_product.get("product", {}).get("properties", []))

    def test_product_ean_gtin(self):
        ean_props = self.product_map.get("product.id.ean")

        if ean_props:
            ean_value = ean_props[0].get("value")
            if ean_value and (len(str(ean_value)) < 11 or not str(ean_value).isdigit()):
                self.errors["prod_ean"].append(self.original_product.get("product", {}).get("properties", []))

    # ... (Other test methods follow similar pattern, using self.errors instead of self.error_list) ...
    # For brevity, I'm including the key logic for the rest of the methods implicitly via the Validator structure
    # You should copy the logic from the original file for test_review_* methods and adapt them to append to self.errors[key]

    def test_review_title(self, xreview_title: list[str]=[]) -> None:
        xreview_title = self.xreview_title + xreview_title
        properties = self.original_product.get("review", {}).get("properties", [])
        title_props = self.product_map.get("review.title")

        if not title_props: return

        property = title_props[0]
        title = property.get("value")
        xtitle = is_include(xreview_title, title)
        if xtitle:
            property["error_name"] = xtitle
            self.errors["rev_title"].append(properties)

    def test_review_date(self) -> None:
        date_props = self.product_map.get("review.publish_date")
        if not date_props:
            self.errors["rev_date"].append(self.original_product.get("review", {}).get("properties", []))

    def test_review_grade(self) -> None:
        grade_props = self.product_map.get("review.grade")
        if not grade_props:
            self.errors["rev_grades"].append(self.original_product.get("review", {}).get("properties", []))

    def test_review_author(self) -> None:
        author_props = self.product_map.get("person.name")
        if not author_props:
            properties = self.original_product.get("review", {}).get("properties", [])
            properties.append({"error_no_author": "No author"})
            self.errors["rev_author"].append(properties)

    def test_review_award(self) -> None:
        award_props = self.product_map.get("review.awards")
        if not award_props:
            properties = self.original_product.get("review", {}).get("properties", [])
            properties.append({"error_no_award": "No award"})
            self.errors["rev_award"].append(properties)

    def test_review_pros_cons(self) -> None:
        temp_pros_cons = None
        properties = self.original_product.get("review", {}).get("properties", [])
        property_pros = self.product_map.get("review.pros", [])
        property_cons = self.product_map.get("review.cons", [])
        pros = [property.get("value") for property in property_pros]
        cons = [property.get("value") for property in property_cons]

        for i, pro in enumerate(pros):
            if pro and len(pro) < 2:
                property_pros[i]["error_len"] = "< 2"
                temp_pros_cons = properties
            if pro in cons:
                property_pros[i]["error_in_con"] = f"Pro: '{pro}' in cons"
                temp_pros_cons = properties
            if pro:
                match = self.pros_cons_regex.search(pro)
                if match:
                    property_pros[i]["error_start_end"] = f"starts or ends with '{match.group(0)}'"
                    temp_pros_cons = properties

        for i, con in enumerate(cons):
            if con and len(con) < 3:
                property_cons[i]["error_len"] = "< 3"
                temp_pros_cons = properties
            if con in pros:
                property_cons[i]["error_in_pro"] = f"Con: '{con}' in pros"
                temp_pros_cons = properties
            if con:
                match = self.pros_cons_regex.search(con)
                if match:
                    property_cons[i]["error_start_end"] = f"starts or ends with '{match.group(0)}'"
                    temp_pros_cons = properties

        if temp_pros_cons:
            self.errors["rev_pros_cons"].append(temp_pros_cons)

    def test_review_conclusion(self, xreview_conclusion: list[str] = []) -> None:
        xreview_conclusions = self.xreview_excerpt + xreview_conclusion
        properties = self.original_product.get("review", {}).get("properties", [])
        conclusion_props = self.product_map.get("review.conclusion")
        if not conclusion_props: return
        property = conclusion_props[0]
        conclusion = property.get("value")
        xreview_conclusion = is_include(xreview_conclusions, conclusion)
        if xreview_conclusion:
            property["error_name"] = xreview_conclusion
            self.errors["rev_conclusion"].append(properties)

    def _check_text_chunk(self, text: str, excerpt: str, len_chank: int) -> str | None:
        """Helper to check if an excerpt is found within chunks of a larger text."""
        if not text or not excerpt:
            return None

        chank_count = len(text) // len_chank
        chunk_list = [text[len_chank * i:len_chank * (i + 1)] for i in range(chank_count)]

        return is_include(chunk_list, excerpt)

    def test_review_excerpt(self, xreview_excerpt: list[str] = [], len_chank: int = 100, len_excerpt: int = 10, not_xrev_excerpt: str|None = None) -> None:
        xreview_excerpts = self.xreview_excerpt + xreview_excerpt
        if not_xrev_excerpt and not_xrev_excerpt in xreview_excerpts:
            xreview_excerpts.remove(not_xrev_excerpt)

        properties = self.original_product.get("review", {}).get("properties", [])
        excerpt_props = self.product_map.get("review.excerpt")

        if not excerpt_props:
            properties.append({"error_no": "No excerpt"})
            self.errors["rev_excerpt"].append(properties)
            return

        excerpt_property = excerpt_props[0]
        excerpt = excerpt_property.get("value")
        if not excerpt:
            return

        has_error = False

        for prop_key, error_key, error_desc in [("summary", "error_in_sum", "summary"), ("conclusion", "error_in_con", "conclusion")]:
            props = self.product_map.get(f"review.{prop_key}")
            if props:
                text_content = props[0].get("value", "")
                element = self._check_text_chunk(text_content, excerpt, len_chank)
                if element:
                    excerpt_property[error_key] = f"This element in {error_desc}: '{element}'"
                    has_error = True

        if len(excerpt) < len_excerpt:
            excerpt_property["error_len"] = f"Len excerpt < {len_excerpt}"
            has_error = True

        xreview_excerpt_found = is_include(xreview_excerpts, excerpt)
        if xreview_excerpt_found:
            excerpt_property["error_name"] = xreview_excerpt_found
            has_error = True

        if has_error:
            self.errors["rev_excerpt"].append(properties)


class TestProductMultiprocessing:
    def __init__(self, product: Product):
        Path("product_test/error").mkdir(exist_ok=True)
        self.products = product.file.get("products")
        self.agent_name = product.agent_name
        self.path = Path(f"product_test/error/{self.agent_name}")
        self.path.mkdir(exist_ok=True)
        self.config = {}

    def worker_task(self, product_data):
        """
        Worker function to process a single product.
        """
        validator = ProductValidator(product_data)
        return validator.validate(self.config)

    def run(self, xproduct_names=[], not_xproduct_name=None, len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[]):
        run_start_time = time.time()

        self.config = {
            'xproduct_names': xproduct_names,
            'not_xproduct_name': not_xproduct_name,
            'len_name': len_name,
            'xreview_title': xreview_title,
            'xreview_conclusion': xreview_conclusion,
            'xreview_excerpt': xreview_excerpt
        }

        with tqdm(total=3, desc="Overall test run") as pbar:
            # Step 1: Validation
            pbar.set_description("Step 1/3: Validating products")
            num_processes = cpu_count()
            num_products = len(self.products)
            logger.info(f"Starting multiprocessing with {num_processes} cores for {num_products} products.")

            # Calculate a reasonable chunksize to improve performance by reducing IPC overhead.
            chunksize = max(1, num_products // (num_processes * 4))
            logger.info(f"Using chunksize: {chunksize} for validation.")

            with Pool(num_processes) as p:
                results = list(tqdm(p.imap(self.worker_task, self.products, chunksize=chunksize), total=num_products, desc=f"Validating products (chunksize={chunksize})", leave=False))

            pool_end_time = time.time()
            logger.info(f"Multiprocessing validation took: {pool_end_time - run_start_time:.2f} seconds")
            pbar.update(1)

            # Step 2: Aggregation
            pbar.set_description("Step 2/3: Aggregating results")
            agg_start_time = time.time()
            logger.info("Aggregating results...")
            aggregated_errors = defaultdict(list)
            for res in results:
                for key, val in res.items():
                    aggregated_errors[key].extend(val)
            agg_end_time = time.time()
            logger.info(f"Result aggregation took: {agg_end_time - agg_start_time:.2f} seconds")
            pbar.update(1)

            # Step 3: Saving
            pbar.set_description("Step 3/3: Saving error files")
            save_start_time = time.time()
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
                logger.error(f"Count error {desc}: {len(errors)}")
                self.save(errors, type_err=key)

            save_end_time = time.time()
            logger.info(f"Saving all error files took: {save_end_time - save_start_time:.2f} seconds")
            pbar.update(1)

        total_run_time = time.time()
        logger.info(f"Total run time: {total_run_time - run_start_time:.2f} seconds")

    def save(self, file: list, type_err: str) -> None:
        file_path = self.path / f"{type_err}.json"
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(file, fd, indent=2, ensure_ascii=False)
