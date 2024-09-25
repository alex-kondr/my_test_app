import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.COMPUTER_TOTAAL
# agent = agents.TEST
reload = 0

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(xproduct_names=[], not_xproduct_name="", len_name=3)     #6
test.test_product_category(xproduct_names=[])
test.test_review_title(xproduct_title=[])
test.test_review_date()
test.test_review_grade()
test.test_review_author()
# test.test_review_award()
test.test_review_pros_cons()    #1
test.test_review_conclusion([])     #1
test.test_review_excerpt([], len_chank=100, len_excerpt=10)     #49

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
