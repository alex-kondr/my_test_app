from agent import *
from models.products import *
import simplejson


X_CATS = ['Top Categories']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.turtlebeach.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cat_names = {
        1: 'Headsets',
        2: 'Simulation',
        3: 'Controllers',
        4: 'Parts & Accessories',
        5: 'Gear',
        6: 'Microphones'
    }

    cats_cnt = 0

    cats = data.xpath('//div[contains(@id, "mobile-linklist-header")][not(@id="mobile-linklist-header-sale")]')
    for cat in cats:
        cats_cnt += 1
        name = cat_names[cats_cnt]

        cats1 = cat.xpath('div[@class="mobile-link-row"]')
        for cat1 in cats1:
            cat1_name = cat1.xpath('span//text()').string()

            subcats = cat1.xpath('div/a[not(contains(text(), "Shop All"))]')
            if not subcats:
                subcats = cat1.xpath('a[not(contains(text(), "All"))]')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string() + "?view=json&page=1"

                if cat1_name and cat1_name not in X_CATS:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + cat1_name + "|" + subcat_name, url=url))
                else:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + subcat_name, url=url))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.xpath('//div[@class="shopify-section"]//text()').string())

    prods = prods_json['collection']['products']
    for prod in prods:
        name = prod['title']
        url = "https://www.turtlebeach.com" + prod['url']
        ssid = prod['id']
        mpn = prod['selectedOrFirstVariantSku']
        ean = prod.get('barcode')
        session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, mpn=mpn, ean=ean))

    page = int(prods_json['collection']['pagination']['page'])
    pages_cnt = int(prods_json['collection']['pagination']['pages'])
    if page < pages_cnt:
        next_url = context['url'].split('?')[0] + "?view=json&page={}".format(page + 1)
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()
    product.ssid = context['ssid']

    mpn = context.get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context.get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//span[@itemprop="ratingCount"]/text()').string()
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = "https://staticw2.yotpo.com/batch/app_key/VDC0UlGBZAONh3AQEdnG0PEWADqhjyiFpfWsXcCD/domain_key/{ssid}/widget/reviews".format(ssid=product.ssid)
        options = "--compressed -X POST --data-raw 'methods=%5B%7B%22method%22%3A%22reviews%22%2C%22params%22%3A%7B%22pid%22%3A%22{ssid}%22%2C%22locale%22%3A%22en%22%2C%22order_metadata_fields%22%3A%7B%7D%2C%22widget_product_id%22%3A%22{ssid}%22%2C%22data_source%22%3A%22default%22%2C%22page%22%3A1%2C%22host-widget%22%3A%22main_widget%22%2C%22is_mobile%22%3Afalse%2C%22pictures_per_review%22%3A10%7D%7D%5D&app_key=ZEa1Oav1ZzMNWody4nMLI90JMSiVOkqkPhQLqAiR&is_mobile=false&widget_version=2023-02-23_08-39-45'".format(ssid=product.ssid)
        session.do(Request(revs_url, use='curl', options=options, force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_url=revs_url, page=1, offset=5))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(str(revs_json[0]["result"]))

    revs = new_data.xpath('//div[contains(@class, "yotpo-review ")]')

    revs_count = new_data.xpath('//div[@class="total-reviews-search"]/@total-reviews-search').string()
    if revs_count and int(revs_count) == 0:
        return


    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev.xpath('.//div[@class="content-title yotpo-font-bold"]//text()').string(multiple=True)
        review.ssid = rev.xpath('@data-review-id').string()
        review.url = product.url
        review.date = rev.xpath('.//span[@class="y-label yotpo-review-date"]//text()').string()

        if review.ssid == '0':
            continue

        syndicated = rev.xpath(".//div[contains(@class,'yotpo-syndication-reference')]//img/@alt").string()
        if syndicated:
            continue

        author = rev.xpath('.//span[@class="y-label yotpo-user-name yotpo-font-bold pull-left"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.xpath('.//div[@class="yotpo-header yotpo-verified-buyer"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.xpath('.//span[@class="sr-only"]//text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(' star ')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        hlp_yes = rev.xpath('.//span[@class="y-label yotpo-sum vote-sum"][@data-type="up"]//text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[@class="y-label yotpo-sum vote-sum"][@data-type="down"]//text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath('.//div[@class="content-review"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)


    page = context['page']
    offset = context['offset']

    if int(revs_count) > offset:
        page += 1
        offset += 5
        url = context['revs_url']
        options = "--compressed -X POST --data-raw 'methods=%5B%7B%22method%22%3A%22reviews%22%2C%22params%22%3A%7B%22pid%22%3A%22{ssid}%22%2C%22locale%22%3A%22en%22%2C%22order_metadata_fields%22%3A%7B%7D%2C%22widget_product_id%22%3A%22{ssid}%22%2C%22data_source%22%3A%22default%22%2C%22page%22%3A{page}%2C%22host-widget%22%3A%22main_widget%22%2C%22is_mobile%22%3Afalse%2C%22pictures_per_review%22%3A10%7D%7D%5D&app_key=ZEa1Oav1ZzMNWody4nMLI90JMSiVOkqkPhQLqAiR&is_mobile=false&widget_version=2023-02-23_08-39-45'".format(page=page, ssid=product.ssid)
        session.do(Request(url, use="curl", options=options, force_charset='utf-8', max_age=0), process_reviews, dict(context, offset=offset, page=page))

    elif product.reviews:
        session.emit(product)
