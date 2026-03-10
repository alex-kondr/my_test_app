from agent import *
from models.products import *
import simplejson


XCAT = ['Gebrauchtes', 'Black Week', 'Black Friday B-Ware', 'Black Friday Trade-Up', 'Black Friday', 'Retouren']


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.projekt-akustik.de/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@id="noscript-navigation"]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string()

                subcats = cat1.xpath('ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url, max_age=0),  process_cat_id, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url, max_age=0),  process_cat_id, dict(cat=name+'|'+cat1_name))


def process_cat_id(data, context, session):
    strip_namespace(data)

    cat_id = data.xpath('//div[@pagetype="articleList"]/@categoryid').string()
    if cat_id:
        url = 'https://www.projekt-akustik.de/apis/react/get-category.php?categoryId={cat_id}/'.format(cat_id=cat_id)
        session.queue(Request(url, max_age=0), process_prodlist, dict(context))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('results', [])
    for prod in prods:
        manufacturer = prod.get('brand', '')
        url = 'https://www.projekt-akustik.de/' + prod.get('link', '')
        if url:
            session.queue(Request(url, max_age=0), process_product, dict(context, url=url, manufacturer=manufacturer))

    next_page = prods_json.get('pagination', {}).get('nextPageUrl')
    if next_page:
        next_url = 'https://www.projekt-akustik.de/apis/react/get-category.php' + next_page
        session.queue(Request(next_url, max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1[contains(@class, "product-title")]/text()').string()
    product.url = context['url']
    product.ssid = data.xpath('//input[contains(@class, "current_article")]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = context.get('manufacturer')

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin13')
        if ean:
            product.add_property(type='id.ean', value=str(ean))

    revs = data.xpath('//div[@class="modal-body"]//div[@class="row"]/div[div[contains(@class, "tsReviewText")]]')
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'

        date = rev.xpath('span[@class="paFontSizeXS paGrey"]/text()').string()
        if date:
            review.date = date.split('am ')[-1]

        author = rev.xpath('span[@class="paFontSizeXS paBold"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('span[@class="paFontSizeMD paBold"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('div[contains(@class, "tsReviewText")]/text()').string()
        if excerpt and len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs
