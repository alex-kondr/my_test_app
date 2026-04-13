from agent import *
from models.products import *
import simplejson


XCAT = ['Marken', 'Sale', 'Software', 'Garantien', 'Kabel & Adapter', 'Service & Wartung']


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
    session.queue(Request("https://apishop.think-about.it/occ/v2/mynotebook/master-categories?lang=de&curr=EUR"), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = simplejson.loads(data.content).get('level1Categories', [])
    for cat in cats:
        name = cat.get('name', {}).get('entry', [{}])[0].get('value')

        if name not in XCAT:
            cats1 = cat.get('level2Categories', [])
            for cat1 in cats1:
                cat1_name = cat1.get('name', {}).get('entry', [{}])[0].get('value')

                if cat1_name not in XCAT:
                    subcats = cat1.get('level3Categories', [])
                    for subcat in subcats:
                        subcat_name = subcat.get('name', {}).get('entry', [{}])[0].get('value')

                        if subcat_name not in XCAT:
                            url = 'https://mynotebook.de/de/c/' + subcat.get('code')
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))




def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-item-info"]')
    for prod in prods:
        name = prod.xpath('.//strong[@class="product name product-item-name"]/a//text()').string(multiple=True)
        url = prod.xpath('.//strong[@class="product name product-item-name"]/a/@href').string(multiple=True)
        ssid = prod.xpath('.//div/@data-product-id').string()

        revs_cnt = prod.xpath('.//div[@class="reviews-actions"]/a/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, revs_cnt=int(revs_cnt)))

    next_url = data.xpath('//li[@class="item pages-item-next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    prod_json = simplejson.loads(data.xpath('//script[@type="application/ld+json"]//text()').string())

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = prod_json.get('brand')
    product.ssid = context['ssid']

    mpn = prod_json.get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = prod_json.get('gtin13')
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_url = "https://mynotebook.de/review/product/listAjax/id/{ssid}/?limit=50".format(ssid=product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=context['revs_cnt']))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//li[@class="item review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time[@itemprop="datePublished"]//text()').string()

        title = rev.xpath('div[@class="review-title"]//text()').string(multiple=True)
        if title:
            title = title.encode("ascii", errors="ignore").strip()
            if title:
                review.title = title

        author = rev.xpath('p[@class="review-author"]/strong//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]//text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.rstrip('%')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('div[@class="review-content"]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.encode("ascii", errors="ignore").strip()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 50
    revs_cnt = context['revs_cnt']
    if revs_cnt > offset:
        next_page = context.get('page', 1) + 1
        revs_url = "https://mynotebook.de/review/product/listAjax/id/{ssid}/?p={page}".format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=revs_cnt, page=next_page, offset=offset))
    elif product.reviews:
        session.emit(product)
