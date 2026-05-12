from agent import *
from models.products import *
import simplejson


CAT = ['Fragrance', 'Sun & Tan', 'Haircare', 'Skincare', 'Makeup', 'Bath & Body', 'Nails', 'Electricals', 'Home & Candles', 'Health & Wellbeing']
XCAT = ['Shop All', 'Gift Sets for her', 'Gift sets for him', 'BEST-SELLERS', 'Best-Sellers']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.justmylook.com/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//nav[@class="h-full"]/ul/ul/div')
    for cat in cats:
        name = cat.xpath('div/h2/text()').string()
        url = cat.xpath('div/div/a/@href').string()

        if name in CAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//a[contains(@class, "group/collection-link")]')
    for subcat in subcats:
        subcat_name = subcat.xpath('.//p/text()').string()
        cat_id = subcat.xpath('@href').string()

        if subcat_name not in XCAT:
            options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'content-type: application/x-www-form-urlencoded' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw '{"requests":[{"indexName":"shopify_products","params":"clickAnalytics=true&distinct=true&facetingAfterDistinct=true&facets=%5B%22meta.algolia.colour_description%22%2C%22meta.algolia.fragrance_classification%22%2C%22meta.algolia.fragrance_notes%22%2C%22meta.algolia.fragrance_type%22%2C%22meta.algolia.gender%22%2C%22meta.algolia.hair_type_concern%22%2C%22meta.algolia.healthcare_concern%22%2C%22meta.algolia.home_fragrance_scent%22%2C%22meta.algolia.key_ingredient%22%2C%22meta.algolia.nail_polish_colour%22%2C%22meta.algolia.product_type%22%2C%22meta.algolia.skin_concern%22%2C%22meta.algolia.skin_type%22%2C%22meta.algolia.spf_content%22%2C%22meta.algolia.supplement_format%22%2C%22meta.algolia.supplement_type%22%2C%22price%22%2C%22price_range%22%2C%22product_type%22%2C%22vendor%22%5D&filters=collections%3A""" + cat_id + """&highlightPostTag=__%2Fais-highlight__&highlightPreTag=__ais-highlight__&hitsPerPage=24&maxValuesPerFacet=200&page=1&query=&ruleContexts=%5B%22""" + cat_id + """%22%2C%22shopify_default_collection%22%5D&userToken=anonymous-d8522922-34ba-46a4-9cab-02fe1f574c28"}]}'"""
            session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods_json = data.xpath('''//script[contains(., '"@type": "ItemList"')]/text()''').string()
    try:
        prods = simplejson.loads(prods_json).get('itemListElement', [])
    except:
        return

    for prod in prods:
        url = prod.get('url')
        session.queue(Request(url), process_product, dict(context, url=url))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.category = context["cat"].title()
    product.sku = context["sku"]
    product.ssid = context["ssid"]
    product.manufacturer = context["manufacturer"]

    prod_data = data.xpath('''//script[contains(., '"AggregateRating"')]/text()''').string()
    if prod_data:
        prod_data = simplejson.loads(prod_data)

        ean = prod_data.get('offers').get('gtin13')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

        revs_cnt = prod_data.get('aggregateRating', {}).get('ratingCount')
        next_page = context.get('page', 0) + 1
        data_sku = context["data_sku"]
        if revs_cnt and int(revs_cnt) > 0:
            if int(revs_cnt) >= 7:
                revs_url = 'https://api.reviews.io/timeline/data?type=product_review&store=just-my-look1&sort=date_desc&page={next_page}&per_page=7&include_sentiment_analysis=true&sku={data_sku}&lang=en&enable_avatars=true&include_subrating_breakdown=1'.format(next_page=str(next_page), data_sku=data_sku)
                session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product, revs_url=revs_url, page=next_page))
            else:
                revs_url = 'https://api.reviews.io/timeline/data?type=product_review&store=just-my-look1&sort=date_desc&page=1&per_page=7&include_sentiment_analysis=true&sku={data_sku}&lang=en&enable_avatars=true&include_subrating_breakdown=1'.format(data_sku=data_sku)
                session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    strip_namespace(data)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    product = context["product"]

    revs = revs_json.get('timeline', [])
    for rev in revs:
        rev = rev.get('_source', {})
        review = Review()
        review.url = product.url
        review.type = "user"
        review.ssid = rev.get('_id').split('-')[-1]

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        author_name = rev.get('author')
        author_ssid = rev.get('user_id')
        if author_name and author_ssid:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('order_id')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        is_recommended = rev.get('would_recommend_product')
        if is_recommended and is_recommended == True:
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('comments')
        if excerpt:
            excerpt = excerpt.replace("\r\n", '').strip()
            excerpt = excerpt.encode("ascii", errors="ignore").strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)