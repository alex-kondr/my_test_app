import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products_multiprocessing import Product, TestProductMultiprocessing, check_code_changes
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.CAMPING_KAUFHAUS_DE
# agent = agents.TEST
reload = 1

# name: 1+
# cat: 16+
# id.man: 3+
# author: 'Peter KaÃ\x9Febaum'


if __name__ == "__main__":
    product = Product(agent, reload=reload)
    print(product.result)
    test = TestProductMultiprocessing(product)
    test.run(xproduct_names=[], not_xproduct_name='', len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[])

    log = LogProduct(agent, reload=reload)
    test_log = TestLogProduct(log)
    test_log.test_log()

    check_code_changes(__file__)
