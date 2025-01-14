from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://matsui.net/product/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="mainItem"]/a')
    for cat in cats:
        name = cat.xpath('div/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="itemBox"]//a')
    for prod in prods:
        title = prod.xpath('@title').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = "Matsui"

    product.name = data.xpath('//div[@class="name"]//span/text()').string()
    if not product.name:
        product.name = data.xpath('//h1[@class="productName"]/text()').string()

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    pros = data.xpath('//h1[contains(.//text(), "の特長")]/following-sibling::h2[not(contains(@class, "SectionTit"))]')
    if not pros:
        pros = data.xpath('//h1[contains(.//text(), "の特長")]/following-sibling::ol/li')

    for pro in pros:
        pro = pro.xpath('.//text() | following-sibling::p[1]//text()').string(multiple=True).split('. ')[-1].split('．')[-1]
        review.add_property(type="pros", value=pro)

    if not pros:
        pros = data.xpath('//h1[contains(@id, "の特長")]/following-sibling::p//strong/parent::*')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True).split('. ')[-1].split('．')[-1]
            review.add_property(type="pros", value=pro)

    summary = data.xpath('//p[@class="productDescription"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//meta[@name="description"]/@content').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//ol/li[not(.//strong)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p/span[contains(.//text(), "●")]//text() | //ol/li//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        if pros and pro in excerpt:
            return

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
