from agent import *
from models.products import *
import simplejson
import re


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.4tochki.ru/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "js-main-nav")]//li[contains(@class, "has-dropdown")]')
    for cat in cats:
        name = cat.xpath('div/a//text()').string(multiple=True)

        subcats = cat.xpath('ul/li/a')
        if subcats:
            for subcat in subcats:
                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))
        else:
            url = cat.xpath('div/a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "item__middle") and div[contains(@class, "item__name")]]')
    for prod in prods:
        name = prod.xpath('div[contains(@class, "item__name")]/a/text()').string()
        url = prod.xpath('div[contains(@class, "item__name")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "item__opinion-text")]/text()').string(multiple=True)
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=int(revs_cnt)))

    next_url = data.xpath('//a[@aria-label="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].replace('', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//li[contains(span, "Артикул")]/b/text()').string()
    product.sku = data.xpath('//input[@name="modelId"]/@value').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(span, "Производитель")]/a/text()').string()

    prod_json = data.xpath('//script[contains(., "window.controllerConfigHead =")]/text()').string()
    match = re.search(r'window\.controllerConfigHead\s*=\s*(\{.*?\});', prod_json)
    if match:
        prod_json = match.group(1)
        prod_json = simplejson.loads(prod_json)
        context['revs_url'] = 'https://www.4tochki.ru' + prod_json.get('allOpinionsLink')

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs = data.xpath('//div[@data-opinionid]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-opinionid').string()
        review.date = rev.xpath('.//span[@class="date"]/text()').string()

        author = rev.xpath('span[@class="name"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('div[contains(@class, "star__rating")]/@class').string()
        if grade_overall:
            grade_overall = grade_overall.split('rating--')[-1].split()[0]
            if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//span[contains(text(), "Товар куплен на 4TOCHKI✅")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('div[not(@class or span)]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    offset = context['offset'] + 20 if context.get('offset') else 3
    if offset < context['revs_cnt'] and context.get('revs_url'):
        next_page = context.get('page', 0) + 1
        next_url = context['revs_url'] + '&page=' + str(next_page)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)