from test_products import Product, TestProduct
from test_logs import LogProduct, TestLogProduct, ResultParse



"19734 - test"
"18011 - colorfoto"
"13600 - music"
"13085 - mixonline"
"13884 - hit.ro"
"15069 - consolewars"

agent_id = 15069

result = ResultParse(agent_id)
print(result)

# product = Product(agent_id, reload=True)
# test = TestProduct(product, xreview_excerpt=["sursa"])
# test.test_product_name()
# test.test_product_category()
# test.test_review_grade()
# test.test_review_pros_cons()
# test.test_review_excerpt()

# log = LogProduct(agent_id, reload=True)
# test_log = TestLogProduct(log)
# test_log.test_log()
