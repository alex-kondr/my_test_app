from agent import *
from models.products import *
import simplejson


CAT = ['Fragrance', 'Sun & Tan', 'Haircare', 'Skincare', 'Makeup', 'Bath & Body', 'Nails', 'Electricals', 'Home & Candles', 'Health & Wellbeing']
XCAT = ['Shop All']


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
        url = subcat.xpath('@href').string()

        if subcat_name not in XCAT:
            
            print context['cat']+'|'+subcat_name, url
            # session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('''//script[@id="web-pixels-manager-setup"]/text()''').string()
    if prods:
        prods = prods.replace("\n","").split('"collection_viewed",')[-1].split(");},\"https://www.justmylook.com/cdn\",")[0]
        prods = simplejson.loads(prods)
        prods = prods.get("collection").get("productVariants")

        if prods:
            for prod in prods:
                name = prod.get("product").get("title")
                url = "https://www.justmylook.com" + prod.get("product").get("url")
                sku = prod.get("sku")
                data_variant_id = prod.get("id")
                ssid = prod.get("product").get("id")
                manufacturer = prod.get("product").get("vendord")
                data_sku = url.replace("https://www.justmylook.com/","") + ";" + sku + ";" + data_variant_id
                session.queue(Request(url), process_product, dict(context, name=name, url=url, sku=sku, ssid=ssid, data_sku=data_sku, manufacturer=manufacturer))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.category = context["cat"]
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