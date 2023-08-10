from tests import Product, Test, LogProduct


"19734 - test"
"18011 - colorfoto"
"13600 - music"
"13085 - mixonline"

product = Product(13600, reload=True)
test = Test(product)
test.test_product_name()
test.test_product_category()
# test.test_review_grade()
test.test_review_pros_cons()
test.test_review_excerpt()

# log = LogProduct(13085, reload=True)
