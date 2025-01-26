from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.bernabei.it/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="mainnav"]/li[position()>1][position()<8]//a[@class="menu-title-lv0"]')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath("@href").string()
        if url:
            session.queue(Request(url), process_category, dict(cat=name, url=url))


def process_category(data, context, session):
    prods = data.xpath('//div[@class="item-title"]//a')
    is_revs_arr = data.xpath('//meta[@itemprop="reviewCount"]/@content')
    for prod, is_revs in zip(prods, is_revs_arr):
        url = prod.xpath('@href').string()
        name = data.xpath('text()').string()
        if url and is_revs.string():
            session.queue(Request(url, force_charset="utf-8"), process_product, dict(context, url=url, name=name, cat=context['cat']))

    next_page = data.xpath('//a[@class="button next"][1]/@href').string()
    if next_page:
        session.queue(Request(next_page, force_charset="utf-8"), process_category, dict(context, url=next_page))


def process_product(data, context, session):
    try:
        json_body = data.xpath("//script[contains(text(), '\"sku\"')]/text()").string()
    except:
        return
    
    resp = simplejson.loads(json_body)

    product = Product()
    product.name = resp['name']
    product.url = context['url']
    product.category = context['cat']
    product.sku = resp['sku']
    product.ssid = product.sku
    product.manufacturer = resp['brand']['name']

    mpn = resp['mpn']
    if mpn:
        product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))
    
    product_id = data.xpath('//input[@name="product"]/@value').string()
    
    reviews_url = 'https://www.bernabei.it//bernabei_customization/index/getreviewsprodotto?product_id={}'.format(product_id)
    session.do(Request(reviews_url), process_review, dict(product=product))


def process_review(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="recensioni-container"]/div[contains(@class, "recensione")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev.xpath('.//div[@class="titolo-recensione"]//text()').string()
        review.url = product.url
        review.date = rev.xpath('.//small[@class="date"]/text()').string()

        author_name = rev.xpath('.//div[@class="autore-recensione"]//text()').string(multiple=True)
        if author_name:
            author_name = author_name.replace("Recensione di", "").strip()
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade = rev.xpath('.//div[@class="rating-box"]/div/@style').string()
        if grade:
            grade = grade.replace('%;', '').replace('width:', '')
            review.grades.append(Grade(type='overall', value=float(grade)/20, best=5.0))

        helpful = rev.xpath('.//a[@class="voteup"]//text()').string(multiple=True)
        if helpful:
            review.add_property(type='helpful_votes', value=int(helpful))

        unhelpful = rev.xpath('.//a[@class="votedown"]//text()').string(multiple=True)
        if unhelpful:
            review.add_property(type='not_helpful_votes', value=int(unhelpful))

        excerpt = rev.xpath('.//div[@class="test-recensione"]//text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            if author_name:
                review.ssid = review.digest()
            else:
                review.ssid = review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
