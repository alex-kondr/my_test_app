import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products_multiprocessing import Product, TestProductMultiprocessing, check_code_changes
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.WEAREMOBIANS_FR
# agent = agents.TEST
reload = 1
session_id = 0

# name: 5+
# category: 0+
# date: 0+
# grades: https://wearemobians.com/2016/07/test-zte-blade-v7-lite/
# excerpt: 15

if __name__ == "__main__":
    product = Product(agent, reload=reload, session_id=session_id)
    print(product.result)
    test = TestProductMultiprocessing(product)
    test.run(xproduct_names=[], not_xproduct_name='', len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[])

    log = LogProduct(agent, reload=reload)
    test_log = TestLogProduct(log)
    test_log.test_log()

    check_code_changes(__file__)
