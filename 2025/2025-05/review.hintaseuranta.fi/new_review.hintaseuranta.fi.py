from agent import *
from models.products import *
import simplejson


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://hintaseuranta.fi/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="navigation"]/ul/li')
    for cat in cats:
        name = cat.xpath('div/a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()

            if name and sub_name:
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name + '|' + sub_name))


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "category-list") and h4]')
    for cat in cats:
        name = cat.xpath('h4//text()').string(multiple=True)

        sub_cats = cat.xpath('ul/li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name))
        else:
            url = cat.xpath('h4/a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods_cnt = data.xpath('//span[@class="search-hits"]/text()').string()
    cat_id = data.response_url.split('?')[0].split('/')[-1]
    next_data = data.xpath('//div[@id="data-values"]//@data-values').string(multiple=True)
    options = """--compressed -X POST  --data-raw 'id={cat_id}&vals={data}&view=&sort=rating+desc'""".format(data=next_data, cat_id=cat_id)

    if prods_cnt and next_data:
        session.do(Request('https://hintaseuranta.fi/facet/filtering', options=options, use='curl', force_charset='utf-8', max_age=0), process_prodlist_sort, dict(context, next_data=next_data, prods_cnt=int(prods_cnt)))


def process_prodlist_sort(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="item-data"]')
    for prod in prods:
        name = prod.xpath('h4[not(@class)]/a/text()').string()
        url = prod.xpath('h4[not(@class)]/a/@href').string()

        rating = prod.xpath('div[@class="item-data-rating"]')
        if rating:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))
        else:
            return

    offset = context.get('offset', 0) + 30
    if offset < context['prods_cnt']:
        options = """--compressed -X POST  --data-raw 'vals={data}&skip={offset}&view=&sort=rating+desc'""".format(data=context['next_data'], offset=offset)
        session.do(Request('https://hintaseuranta.fi/facet/listmore', options=options, use='curl', force_charset='utf-8', max_age=0), process_prodlist_sort, dict(context, offset=offset))


def process_product(data, context, session):
    strip_namespace(data)

    product= Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        ean = prod_json.get('gtin13')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//table[@id="productReviews"]/tbody/tr[.//div]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//a[contains(@href, "reviewId")]/@href').string().split('=')[-1]

        date = rev.xpath('.//td[h4]/text()').string(multiple=True)
        if date:
            review.date = date.strip('( )')

        author = rev.xpath('.//td[h4]/strong/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//i[contains(@class, "stars")]/@class').string()
        if grade_overall:
            grade_overall = grade_overall.split('pos-x-m')[-1]
            if grade_overall.isdigit():
                grade_overall = (130 - int(grade_overall)) / 26.
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_recommended = rev.xpath('.//div[contains(., "SUOSITTELEN")]')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.xpath('.//span[contains(@id, "votes")]/text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.xpath('.//td/h4/text()').string()
        excerpt = rev.xpath('.//td/p//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\n', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
