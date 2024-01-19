import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.GAME_PRO
# agent = agents.TEST
reload = 1


if __name__ == "__main__":
    product = Product(agent, reload=reload)
    print(product.result)
    test = TestProduct(product)
    test.run(xproduct_names=[], len_name=3, xreview_title=[], xreview_conclusion=[], xreview_excerpt=[])
    # test.test_product_name(xproduct_names=[], not_xproduct_name="", len_name=3)
    # test.test_product_category(xproduct_names=[])
    # test.test_product_sku()
    # test.test_product_id_manufacturer()
    # test.test_product_ean_gtin()
    # test.test_review_title(xproduct_title=[])
    # test.test_review_date()
    # test.test_review_grade()
    # test.test_review_author()
    # # test.test_review_award()
    # test.test_review_pros_cons()    #1
    # test.test_review_conclusion([])
    # test.test_review_excerpt([], len_chank=100, len_excerpt=10)

    log = LogProduct(agent, reload=reload)
    test_log = TestLogProduct(log)
    test_log.test_log()
