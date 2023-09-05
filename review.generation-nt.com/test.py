import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


agent = agents.GENERATION_NT
# agent = agents.TEST
reload = 1

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(xproduct_names=['god'], not_xproduct_name="", len_name=3)    #12
test.test_product_category(xproduct_names=[])
test.test_review_title()
# test.test_review_grade()
test.test_review_author()
# test.test_review_award()
test.test_review_pros_cons()    #15
test.test_review_conclusion(["La discussion est réservée aux membres GNT",
                             "sponsored",
                             "en précommande et sera disponible",
                             "Caractéristiques",
                             "Commencez par",
                             "Copyright ©"
                             ])
test.test_review_excerpt(["La discussion est réservée aux membres GNT",
                          "sponsored",
                          "en précommande et sera disponible",
                          "Caractéristiques",
                          "Commencez par",
                          "Copyright ©"
                          ], len_chank=100, len_excerpt=10)

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
