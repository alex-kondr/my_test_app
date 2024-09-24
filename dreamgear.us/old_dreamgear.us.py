from agent import *
from models.products import *


def process_prodlist(data, context, session):
    prods = data.xpath("//h3[@class='product-item-title']/a")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(name=name, url=url))

    nexturl = data.xpath("//li[@class='next']/a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = 'Equipment for gamers'
    product.ssid = context['url'].split('/')[-2]
    product.manufacturer = 'dreamGEAR'
    product.sku = data.xpath("//span[@data-product-sku='data-product-sku']/text()").string()
    ean = data.xpath("//div[contains(@class, 'product-info-UPC')][1]//span[@class='product-info-value']//text()").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    pros = data.xpath("//p/strong[contains(., 'Features')]/following-sibling::text()")
    if pros:
        for pro in pros:
            pro = pro.string().replace('•', '').strip()
            if pro:
                review.add_property(type='pros', value=pro)
         
    excerpt = data.xpath("//div[@class='product-description rte']//text()").string(multiple=True).split('Features')[0].split("Includes")[0].split('Download')[0]
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        product.reviews.append(review)
        session.emit(product)
       

def run(context, session):
    session.queue(Request('https://www.dreamgear.com/shop-by-type/'), process_prodlist, dict())
