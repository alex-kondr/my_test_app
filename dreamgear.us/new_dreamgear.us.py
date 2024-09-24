from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.dreamgear.com/browse-by-type/', use='curl'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="product-item-title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_product, dict(name=name, url=url))

    next_url = data.xpath('//li[@class="next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Equipment for gamers'
    product.manufacturer = 'dreamGEAR'
    product.sku = data.xpath("//span[@data-product-sku='data-product-sku']/text()").string()

    ean = data.xpath('//p[contains(., "UPC:")]//text()').string(multiple=True)
    if ean:
        ean = ean.split('UPC')[-1].strip(' :').split()[0].strip()
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = context['url']
    review.ssid = product.ssid

    pros = data.xpath('//p[regexp:test(., "Features|FEATURES")]/following-sibling::p[regexp:test(., "^•")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('•', '').strip()
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    excerpt = data.xpath('//p[regexp:test(., "Features|FEATURES")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "Product info|PRODUCT INFO")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "Includes|INCLUDES")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "Download|DOWNLOAD")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='product-description rte']//text()").string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
