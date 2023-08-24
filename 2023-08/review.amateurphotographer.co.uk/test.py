import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
parent = os.path.dirname(parent)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents

quit()
agent = agents.AMATEURPHOTOGRAPHER
# agent = agents.TEST
reload = 1

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(not_xproduct_name="", len_name=8)
test.test_product_category()
test.test_review_title()
test.test_review_grade()
test.test_review_author()
test.test_review_pros_cons()
test.test_review_conclusion(["Read our full", "Related reading", "Our verdict", "Related articles:"])#, "pecification"])
test.test_review_excerpt(["Read our full", "Related reading", "Our verdict", "Related articles:"], len_chank=300, len_excerpt=10)# "Specification"])

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
