import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.MIXONLINE
# agent = agents.TEST
reload = 1

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(not_xproduct_name="", len_name=8)
test.test_product_category(xproduct_names=["new", "blog", "home"])
test.test_review_title()
test.test_review_grade()
test.test_review_author()
test.test_review_pros_cons()
test.test_review_conclusion(["Product Summary", "PRODUCT SUMMARY", "CONS:", "PROS:", "PRICE:", "PRODUCT:", "COMPANY:"])
test.test_review_excerpt(["Product Summary", "PRODUCT SUMMARY", "CONS:", "PROS:", "PRICE:", "Price:", "PRODUCT:", "COMPANY:"], len_chank=200, len_excerpt=10)

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
