from pathlib import Path
import json
import logging
import sys
import re
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from product_test.functions import load_file


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


def process_log_chunk(chunk: list[str]) -> list[list[str]]:
    """
    Processes a chunk of log lines to find errors and their preceding request URL.
    """
    errors_in_chunk = []
    error_pattern = re.compile(r"error ", re.IGNORECASE)
    request_pattern = re.compile(r"Request GET u'([^']*)'")
    for i, line in enumerate(chunk):
        if error_pattern.search(line):
            context_url = "URL not found"
            # Search backwards from the error line for the most recent request URL.
            for j in range(i - 1, max(i - 20, -1), -1):
                context_line = chunk[j]
                match = request_pattern.search(context_line)
                if match:
                    context_url = match.group(1)
                    break
            errors_in_chunk.append([context_url, line])
    return errors_in_chunk


class LogProduct:
    def __init__(self, agent_id: int, reload=False):
        self.agent_id = agent_id
        self.emits_dir = Path("product_test/logs")
        self.emits_dir.mkdir(exist_ok=True)
        self.file_path = self.emits_dir / f"agent-{self.agent_id}.json"

        if not self.file_path.exists() or reload:
            self.file = self.generate_file()
        else:
            logger.info(f"Opening existing log file: {self.file_path}")
            self.file = self.open_file()

    def generate_file(self) -> list:
        logger.info(f"Getting logs for agent {self.agent_id}...")
        content = load_file(agent_id=self.agent_id, type_file="log", decode=True)
        content_list = content.split("\n")
        logger.info(f"Get logs complete ({len(content_list)} lines). Saving logs...")
        self.save_file(content_list)
        logger.info("Logs saved successfully.")
        return content_list

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
        self.path = Path(f"product_test/error/log-{self.log_product.agent_id}")
        self.path.mkdir(exist_ok=True)

    def test_log(self):
        log_lines = self.log_product.file
        if not log_lines:
            logger.warning("Log file is empty, skipping test.")
            return

        num_processes = cpu_count()
        chunk_size = max(1000, len(log_lines) // (num_processes * 2))
        chunks = [log_lines[i:i + chunk_size] for i in range(0, len(log_lines), chunk_size)]

        logger.info(f"Starting log analysis with {num_processes} cores, processing {len(chunks)} chunks.")

        error_log = []
        with Pool(num_processes) as p:
            results_iterator = p.imap_unordered(process_log_chunk, chunks)
            for chunk_errors in tqdm(results_iterator, total=len(chunks), desc="Analyzing logs"):
                if chunk_errors:
                    error_log.extend(chunk_errors)

        logger.info(f"Analyzed {len(log_lines)} log lines.")
        logger.error(f"Find error in logs: {len(error_log)}")
        self.save(error_log)

    def save(self, error_log: list):
        file_path = self.path / "log.json"
        logger.info(f"Saving error log to: {file_path}")
        with open(file_path, "w", encoding="utf-8") as fd:
            json.dump(error_log, fd, indent=2)
