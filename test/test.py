from tests import Product, TestProduct, LogProduct, TestLogProduct


"19734 - test"
"18011 - colorfoto"
"13600 - music"
"13085 - mixonline"

# product = Product(19734, reload=False)
# test = TestProduct(product)
# test.test_product_name()
# test.test_product_category()
# # test.test_review_grade()
# test.test_review_pros_cons()
# test.test_review_excerpt()

log = LogProduct(19734, reload=False)
test_log = TestLogProduct(log)
test_log.test_log()
