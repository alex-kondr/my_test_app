import urllib3
import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


urllib3.disable_warnings()

# agent = agents.AMATEURPHOTOGRAPHER
agent = agents.TEST

product = Product(agent, reload=True)
print(product.result)
test = TestProduct(product)
test.test_product_name()
test.test_product_category()
# test.test_review_grade()
test.test_review_author()
test.test_review_pros_cons()
test.test_review_conclusion(["Read our full", "Related reading", "Our verdict"])#, "pecification"])
test.test_review_excerpt(["Read our full", "Related reading", "Our verdict"], len_chank=300)# "Specification"])

log = LogProduct(agent, reload=True)
test_log = TestLogProduct(log)
test_log.test_log()
