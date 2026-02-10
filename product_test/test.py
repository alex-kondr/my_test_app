import urllib3

from test_products_multiprocessing import Product, TestProductMultiprocessing, check_code_changes
from test_logs import LogProduct, TestLogProduct
import list_of_agents


urllib3.disable_warnings()

agent = list_of_agents.AMATEURPHOTOGRAPHER

# The ResultParse class is available in test_products_multiprocessing as well
# result = ResultParse(agent)
# print(result)

product = Product(agent, reload=True)
test = TestProductMultiprocessing(product)
test.run(
    xreview_conclusion=["Read our full"],
    xreview_excerpt=["Read our full"]
)

log = LogProduct(agent, reload=True)
test_log = TestLogProduct(log)
test_log.test_log()

# At the end, check for code changes in the project directory
check_code_changes()
