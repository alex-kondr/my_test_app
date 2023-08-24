import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.test_products import Product, TestProduct
from product_test.test_logs import LogProduct, TestLogProduct
import product_test.list_of_agents as agents


# agent = agents.EXOPHASE
agent = agents.TEST
reload = 1

product = Product(agent, reload=reload)
print(product.result)
test = TestProduct(product)
test.test_product_name(not_xproduct_name="", len_name=3)
test.test_product_category()
test.test_review_title()
test.test_review_grade()
test.test_review_author()
test.test_review_pros_cons()
test.test_review_conclusion(["The Verdict", "Conclusion", "Final word", "Score", "Verdict", "out of", "Verdict", "What Didn’t", "Sticky", "Detention", "The Bad", "The bad", "What Impressed", "Playtime", "Sweet", "The Good", "The good", "Follow this author"])
test.test_review_excerpt(["Reviewed on", "The Verdict", "Conclusion", "Final word", "Verdict", "Verdict", "What Didn’t", "Sticky", "Detention", "The Bad", "What Impressed", "Playtime", "The Good", "Follow this author"], len_chank=200, len_excerpt=10) #"The good","Sweet", "Score", "The bad",

log = LogProduct(agent, reload=reload)
test_log = TestLogProduct(log)
test_log.test_log()
