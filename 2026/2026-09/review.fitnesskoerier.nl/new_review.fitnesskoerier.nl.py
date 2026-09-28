from agent import *
from models.products import *
import simplejson


XCAT = ['Summer Deals']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.fitnesskoerier.nl'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[contains(@class, "level-1-item")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "level-2-item")]')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('a/text()').string()

                    subcats = cat1.xpath('.//div[contains(@class, "level-3-item")]/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()

                            if 'Alle merken' not in subcat_name:
                                session.queue(Request(url), process_prodlist, dict(cat=name+"|"+cat1_name+"|"+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+"|"+cat1_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//a[@class="item-name"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-id').string()
    product.sku= product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//span[@class="brand-name"]/text()').string()

    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    try:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json[-1].get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json[-1].get('gtin13')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    revs = data.xpath('//div[@id="reviews"]//div[@class="review-container"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath('.//span[@class="review-date"]/text()').string()
        if date:
            review.date = date.rsplit(' ', 1)[-1]

        author = rev.xpath('.//span[@class="reviewer"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('@data-score').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//p[@class="content"]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('"', "'").replace('\\n', '').replace('\n', '').strip()

            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# loaded all reviews
