from time import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

import logging

log_format = "%(asctime)s [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s"

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter(log_format))


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    return logger


time_start = time()

CPU_COUNT = cpu_count()
executor = ProcessPoolExecutor(2 * CPU_COUNT + 1)

range_ = 10**5

def print_numb(i):
    log = get_logger(__name__)
    log.error(f'{i=}')
    # log.log(level=0, msg=f'{i=}')
    # print(f"{i=}")


def main1():
    for i in range(range_):
        # log = get_logger('print')
        # log.log(level=0, msg=f'{i=}')
        print_numb(i)

def main():
    # with ProcessPoolExecutor(2 * CPU_COUNT + 1) as executor:
    for i in range(range_):
        executor.submit(print_numb, i)

    executor.shutdown()


if __name__ == "__main__":
    main1()
    print(time() - time_start)
