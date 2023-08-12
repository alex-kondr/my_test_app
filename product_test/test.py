import urllib3

from test_products import Product, TestProduct
from test_logs import LogProduct, TestLogProduct
import list_of_agents


urllib3.disable_warnings()

agent = list_of_agents.AMATEURPHOTOGRAPHER

# result = ResultParse(agent)
# print(result)

product = Product(agent, reload=True)
test = TestProduct(product)#, xreview_excerpt=["sursa"])
test.test_product_name()
test.test_product_category()
# test.test_review_grade()
test.test_review_pros_cons()
test.test_review_conclusion(["Read our full"])
test.test_review_excerpt(["Read our full"])

log = LogProduct(agent, reload=True)
test_log = TestLogProduct(log)
test_log.test_log()
