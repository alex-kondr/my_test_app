from agent import *
from models.products import *
import simplejson
import re


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.bargainmax.co.uk/", use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@data-menu-id="toys"]/div[@class="group/child"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if 'View All' not in name:
            sub_cats = cat.xpath('.//ul/li/a')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()

                    if 'View All' not in sub_name:
                        session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_category, dict(cat=name+'|'+sub_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_category, dict(cat=name))


def process_category(data, context, session):
    cat_name = data.xpath('//div[@class="nosto_category"]/span[@class="category_string"]/text()').string()
    cat_id = data.xpath('//div[@class="nosto_category"]/span[@class="id"]/text()').string()
    options = '''--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Encoding: deflate' -H 'Content-Type: text/plain' -H 'X-Nosto-Integration: Search Templates' --data-raw '{"query":"query ( $abTests: [InputSearchABTest!], $accountId: String, $query: String, $segments: [String!], $rules: [String!], $products: InputSearchProducts, $keywords: InputSearchKeywords, $sessionParams: InputSearchQuery ) { search( accountId: $accountId query: $query segments: $segments rules: $rules products: $products keywords: $keywords sessionParams: $sessionParams abTests: $abTests ) { query redirect products { hits { productId url name imageUrl imageHash thumbUrl description brand variantId availability price priceText categoryIds categories customFields { key value } priceCurrencyCode datePublished listPrice unitPricingBaseMeasure unitPricingUnit unitPricingMeasure googleCategory gtin ageGroup gender condition alternateImageUrls ratingValue reviewCount inventoryLevel skus { id name price listPrice priceText url imageUrl inventoryLevel customFields { key value } availability } pid onDiscount extra { key value } saleable available tags1 tags2 tags3 } total size from facets { ... on SearchTermsFacet { id field type name data { value count selected visual { type value } } } ... on SearchStatsFacet { id field type name min max } } collapse fuzzy categoryId categoryPath } abTests { id activeVariation { id } } } }","variables":{"accountId":"shopify-68485578920","products":{"facets":["*"],"categoryId":"''' + cat_id + '''","categoryPath":"''' + cat_name + '''","size":24,"from":0},"sessionParams":{"segments":["613aa0000000000000000002","61c26a800000000000000002","5b71f1500000000000000006","68cc3a1b8f3fdc2de7ead2ba"],"products":{"personalizationBoost":[{"field":"affinities.categories","weight":0.625,"value":["dolls"]},{"field":"affinities.categories","weight":0.5,"value":["dolls & playsets"]},{"field":"affinities.categories","weight":0.25,"value":["all","standard size","fashion dolls"]},{"field":"affinities.brand","weight":1,"value":["barbie"]},{"field":"affinities.productType","weight":1,"value":["simple"]}]}},"abTests":[]}}\''''
    session.do(Request('https://search.nosto.com/v1/graphql', use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context, cat_name=cat_name, cat_id=cat_id))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content).get('data', {}).get('search', {}).get('products', {})
    except:
        if context.get('options'):
            return

        options = '''--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Encoding: deflate' -H 'Content-Type: text/plain' -H 'X-Nosto-Integration: Search Templates' --data-raw '{"query":"query ( $abTests: [InputSearchABTest!], $accountId: String, $query: String, $segments: [String!], $rules: [String!], $products: InputSearchProducts, $keywords: InputSearchKeywords, $sessionParams: InputSearchQuery ) { search( accountId: $accountId query: $query segments: $segments rules: $rules products: $products keywords: $keywords sessionParams: $sessionParams abTests: $abTests ) { query redirect products { hits { productId url name imageUrl imageHash thumbUrl description brand variantId availability price priceText categoryIds categories customFields { key value } priceCurrencyCode datePublished listPrice unitPricingBaseMeasure unitPricingUnit unitPricingMeasure googleCategory gtin ageGroup gender condition alternateImageUrls ratingValue reviewCount inventoryLevel skus { id name price listPrice priceText url imageUrl inventoryLevel customFields { key value } availability } pid onDiscount extra { key value } saleable available tags1 tags2 tags3 } total size from facets { ... on SearchTermsFacet { id field type name data { value count selected visual { type value } } } ... on SearchStatsFacet { id field type name min max } } collapse fuzzy categoryId categoryPath } abTests { id activeVariation { id } } } }","variables":{"accountId":"shopify-68485578920","products":{"facets":["*"],"categoryId":"''' + context['cat_id'] + '''","categoryPath":"''' + context['cat_name'] + '''","size":24,"from":0},"sessionParams":{"segments":["613aa0000000000000000002","61c26a800000000000000002","68cc3a1b8f3fdc2de7ead2ba","5a497a000000000000000002"],"products":{"personalizationBoost":[{"field":"affinities.categories","weight":0.46153846153846156,"value":["dolls & playsets"]},{"field":"affinities.categories","weight":0.4230769230769231,"value":["simple","standard size shipping","all","in stock items"]},{"field":"affinities.brand","weight":0.2727272727272727,"value":["jurassic world","bargainmax"]},{"field":"affinities.brand","weight":0.18181818181818182,"value":["barbie"]},{"field":"affinities.brand","weight":0.09090909090909091,"value":["cocomelon","disney frozen"]},{"field":"affinities.productType","weight":1,"value":["simple"]}]}},"abTests":[]}}\''''
        session.do(Request('https://search.nosto.com/v1/graphql', use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context, options=options))
        return

    prods = prods_json.get('hits', [])
    for prod in prods:
        product = Product()
        product.ssid = str(prod.get('productId'))
        product.name = prod.get('name')
        product.url = prod.get('url')
        product.category = context['cat']
        product.manufacturer = prod.get('brand')

        skus = prod.get('skus', [])
        sku_code = ''
        if skus:
            product.sku = str(skus[0].get('id'))

            customFields_skus = skus[0].get('customFields')
            for field in customFields_skus:
                if 'skucode' in field.get('key'):
                    sku_code = str(field.get('value'))

        revs_cnt = 0
        custom_fields = prod.get('customFields', [])
        for field in custom_fields:
            if '-mpn' in field.get('key') and field.get('value') and len(field.get('value')) > 1:
                product.add_property(type='id.manufacturer', value=field.get('value'))

            elif 'reviewscouk-total' in field.get('key'):
                revs_cnt_ = field.get('value')
                if revs_cnt_ and revs_cnt_.isdigit():
                    revs_cnt = int(revs_cnt_)

        ean = prod.get('gtin')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))

        if revs_cnt:
            revs_url = 'https://api.reviews.io/timeline/data?type=product_review&store=bargainmax&sort=date_desc&page=1&per_page=100&sku={sku_code}%3B{sku}%3B{ssid}%3B{url}&enable_avatars=false&include_subrating_breakdown=1&must_have_comments=true&branch=&tag=&include_product_reviews=1&lang=en'.format(sku_code=sku_code, sku=product.sku, ssid=product.ssid, url=product.url.split('/')[-1])
            session.do(Request(revs_url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt, sku_code=sku_code))

    prods_cnt = prods_json.get('total')
    offset = context.get('offset', 0) + 24
    if offset < prods_cnt:
        options = '''--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Encoding: deflate' -H 'Content-Type: text/plain' -H 'X-Nosto-Integration: Search Templates' --data-raw '{"query":"query ( $abTests: [InputSearchABTest!], $accountId: String, $query: String, $segments: [String!], $rules: [String!], $products: InputSearchProducts, $keywords: InputSearchKeywords, $sessionParams: InputSearchQuery ) { search( accountId: $accountId query: $query segments: $segments rules: $rules products: $products keywords: $keywords sessionParams: $sessionParams abTests: $abTests ) { query redirect products { hits { productId url name imageUrl imageHash thumbUrl description brand variantId availability price priceText categoryIds categories customFields { key value } priceCurrencyCode datePublished listPrice unitPricingBaseMeasure unitPricingUnit unitPricingMeasure googleCategory gtin ageGroup gender condition alternateImageUrls ratingValue reviewCount inventoryLevel skus { id name price listPrice priceText url imageUrl inventoryLevel customFields { key value } availability } pid onDiscount extra { key value } saleable available tags1 tags2 tags3 } total size from facets { ... on SearchTermsFacet { id field type name data { value count selected visual { type value } } } ... on SearchStatsFacet { id field type name min max } } collapse fuzzy categoryId categoryPath } abTests { id activeVariation { id } } } }","variables":{"accountId":"shopify-68485578920","products":{"facets":["*"],"categoryId":"''' + context['cat_id'] + '''","categoryPath":"''' + context['cat_name'] + '''","size":24,"from":''' + str(offset) + '''},"sessionParams":{"segments":["613aa0000000000000000002","61c26a800000000000000002","5b71f1500000000000000006","68cc3a1b8f3fdc2de7ead2ba"],"products":{"personalizationBoost":[{"field":"affinities.categories","weight":0.625,"value":["dolls"]},{"field":"affinities.categories","weight":0.5,"value":["dolls & playsets"]},{"field":"affinities.categories","weight":0.25,"value":["all","standard size","fashion dolls"]},{"field":"affinities.brand","weight":1,"value":["barbie"]},{"field":"affinities.productType","weight":1,"value":["simple"]}]}},"abTests":[]}}\''''
        if context.get('options'):
            options = '''--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Encoding: deflate' -H 'Content-Type: text/plain' -H 'X-Nosto-Integration: Search Templates' --data-raw '{"query":"query ( $abTests: [InputSearchABTest!], $accountId: String, $query: String, $segments: [String!], $rules: [String!], $products: InputSearchProducts, $keywords: InputSearchKeywords, $sessionParams: InputSearchQuery ) { search( accountId: $accountId query: $query segments: $segments rules: $rules products: $products keywords: $keywords sessionParams: $sessionParams abTests: $abTests ) { query redirect products { hits { productId url name imageUrl imageHash thumbUrl description brand variantId availability price priceText categoryIds categories customFields { key value } priceCurrencyCode datePublished listPrice unitPricingBaseMeasure unitPricingUnit unitPricingMeasure googleCategory gtin ageGroup gender condition alternateImageUrls ratingValue reviewCount inventoryLevel skus { id name price listPrice priceText url imageUrl inventoryLevel customFields { key value } availability } pid onDiscount extra { key value } saleable available tags1 tags2 tags3 } total size from facets { ... on SearchTermsFacet { id field type name data { value count selected visual { type value } } } ... on SearchStatsFacet { id field type name min max } } collapse fuzzy categoryId categoryPath } abTests { id activeVariation { id } } } }","variables":{"accountId":"shopify-68485578920","products":{"facets":["*"],"categoryId":"''' + context['cat_id'] + '''","categoryPath":"''' + context['cat_name'] + '''","size":24,"from":''' + str(offset) + '''},"sessionParams":{"segments":["613aa0000000000000000002","61c26a800000000000000002","68cc3a1b8f3fdc2de7ead2ba","5a497a000000000000000002"],"products":{"personalizationBoost":[{"field":"affinities.categories","weight":0.46153846153846156,"value":["dolls & playsets"]},{"field":"affinities.categories","weight":0.4230769230769231,"value":["simple","standard size shipping","all","in stock items"]},{"field":"affinities.brand","weight":0.2727272727272727,"value":["jurassic world","bargainmax"]},{"field":"affinities.brand","weight":0.18181818181818182,"value":["barbie"]},{"field":"affinities.brand","weight":0.09090909090909091,"value":["cocomelon","disney frozen"]},{"field":"affinities.productType","weight":1,"value":["simple"]}]}},"abTests":[]}}\''''

        session.do(Request('https://search.nosto.com/v1/graphql', use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context, offset=offset))


def process_reviews(data, context, session):
    product = context["product"]

    try:
        revs = simplejson.loads(data.content).get('timeline', [])
    except:
        return

    for rev in revs:
        rev = rev.get('_source', {})

        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        author = rev.get('author')
        author_ssid = rev.get('user_id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_recommended = rev.get('would_recommend_product')
        if is_recommended:
            review.add_property(value=True, type='is_recommended')

        is_verified = rev.get('verified_by_shop')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('review_title')
        excerpt = rev.get('comments')
        if excerpt and len(remove_emoji(excerpt).replace('\r\n', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).replace('\r\n', '').strip()

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                ssid = str(rev.get('_id'))
                if ssid:
                    review.ssid = ssid.split('-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://api.reviews.io/timeline/data?type=product_review&store=bargainmax&sort=date_desc&page={next_page}&per_page=100&sku={sku_code}%3B{sku}%3B{ssid}%3B{url}&enable_avatars=false&include_subrating_breakdown=1&must_have_comments=true&branch=&tag=&include_product_reviews=1&lang=en'.format(sku_code=context['sku_code'], sku=product.sku, ssid=product.ssid, url=product.url.split('/')[-1], next_page=next_page)
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
