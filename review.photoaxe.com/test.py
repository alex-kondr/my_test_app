import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
# parent = os.path.dirname(parent)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.PHOTOAXE
# agent = agents.TEST
reload = 1

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(not_xproduct_name="", len_name=8)
test.test_product_category(xproduct_names=["Other"])
# test.test_product_sku()
# test.test_product_id_manufacturer()
# test.test_product_ean_gtin()
test.test_review_title()
# test.test_review_grade()
test.test_review_author()
# test.test_review_pros_cons()
test.test_review_conclusion(["Specifications", "Functions", "Technical"])
test.test_review_excerpt(["Specifications", "Functions", "Technical"], len_chank=200, len_excerpt=10)

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
