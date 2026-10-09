from agent import *
from models.products import *
import simplejson


XCAT = ['Tutti i vini', 'Altro', 'Magazine']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bernabei.it'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[contains(@class, "topmenu")]/ul/li[contains(@class, "main")]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "item")]/a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//ul[contains(@aria-label, "Submenu for")]/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div[contains(@class, "text")]//text()').string(multiple=True)

                subcats = cat1.xpath('.//ul/li//a')
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string()
                    url = subcat.xpath('@href').string()

                    if name and cat1_name and subcat_name:
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-info")]//a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//form[@id="product_addtocart_form"]//input[@name="product"]/@value').string()
    product.sku = data.xpath('//form[@id="product_addtocart_form"]/@data-sku').string()
    product.category = context['cat']

    try:
        prod_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin13')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))
    except:
        pass

    revs_cnt = data.xpath('//div[contains(@class, "rating-summary")]//span[contains(@class, "text-body")]/text()').string()
    if revs_cnt:
        revs_cnt = int(revs_cnt.split()[0].strip('( )'))
        if revs_cnt > 0:
            revs_url = 'https://www.bernabei.it/bernabei-review/ajax/reviews?product_id={}&page=1'.format(product.ssid)
            session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
        new_data = data.parse_fragment(revs_json.get('html').replace(r'\n', ''))
        revs = new_data.xpath('.//div[contains(@class, "container")]')
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('div[contains(@class, "text-tiny")]/span/text()').string()
        if author and author.strip():
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div/*[contains(name(), "svg")]/*[contains(name(), "g")])')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//div[contains(@class, "text-body")]/text()').string()
        excerpt = rev.xpath('.//div[@x-ref="text"]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' ?+*.')) > 2:
            if title:
                review.title = title.strip(' ?+*.')
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' +*.?')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.bernabei.it/bernabei-review/ajax/reviews?product_id={ssid}&page={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
