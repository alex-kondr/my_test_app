import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


# agent = agents.HIT_RO
agent = agents.TEST
reload = True

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(not_xproduct_name="test")
test.test_product_category()
test.test_review_title()
test.test_review_grade()
test.test_review_author()
test.test_review_pros_cons()
test.test_review_conclusion(["Sursa:", "Surse:", "Specificatii "])
test.test_review_excerpt(["Sursa:", "Surse:", "Specificatii "], len_chank=300, len_excerpt=10)

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
