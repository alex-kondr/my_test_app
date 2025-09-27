import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.DDAY_IT_IT
# agent = agents.TEST
reload = 1

# name: 238
# exc: 6
# https://www.dday.it/redazione/11156/beats-studio-in-prova-quelle-veramente-false.html

if __name__ == "__main__":
    product = Product(agent, reload=reload)
    print(product.result)
    test = TestProduct(product)
    test.run(xproduct_names=[], not_xproduct_name='', len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[])

    log = LogProduct(agent, reload=reload)
    test_log = TestLogProduct(log)
    test_log.test_log()
