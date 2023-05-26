import re

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak()]
    session.queue(Request("https://www.foxtrot.com.ua/uk"), process_frontpage, dict())
    

def process_frontpage(data, context, session):
    cats1 = data.xpath("//ul[@class='menu vertical drilldown']/li")
    cats1 = data.xpath("//ul[@class='catalog__category smooth-scroll']/li")
    for cat1 in cats1:
        name1 = cat1.xpath("div/p//text()").string()
        cats2 = cat1.xpath("div/div/div/div/div")
        for cat2 in cats2:
            name2 = cat2.xpath("div/a//text()").string()
            cats3 = cat2.xpath("a")
            for cat3 in cats3:
                name3 = cat3.xpath(".//text()").string()
                url = cat3.xpath("@href").string()
                session.queue(Request(url), process_category, dict(cat=name1+"|"+name2+"|"+name3))
                

def process_category(data, context, session):
    prods = data.xpath('//div[@class="card__body"]')
    for prod in prods:
        url = prod.xpath("a/@href").string()
        name = prod.xpath(".//a//text()").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product-box__right"]/div/@data-brand').string()

    # SKU - product.sku
    # EAN / GTIN - product.add_property(type='id.ean', value=ean)
    # MPN - product.add_property(type='id.manufacturer', value=ean)
    ean = re.search(r"\(\w+\)$", product.name)[0]
    if ean:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    revs_url = data.xpath('//li/a[@data-mobile="False"]/@href')[0].string()
    if revs_url:
        session.do(Request(revs_url), process_reviews, dict(context, revs_url=revs_url))
    else:
        process_reviews(data, context, session)
        
    
def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="main-reviews__body js-toggle-body"]/div[@class="main-reviews_comments-block-scroll smooth-scroll"]')
    for rev in revs:
        review = Review()
        review.type = "user" # pro / user
        review.url = context.get('revs_url', product.url)
        review.title = ""
        
        
        review.date = rev.xpath('.//div[@class="product-comment__item-date"]').string()
        author = rev.xpath('.//div[@class="product-comment__item-title"]//text()').string()
        review.authors.append(Person(name=author, ssid=author)) # profile_url

        # grade_overall
        grade_overall = rev.xpath('.//div[@class="product-comment__item-rating"]/i[@class="icon icon-star-filled icon_orange"]')
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=len(grade_overall), best=5.0))

        """"""
        excerpt = rev.xpath(".//span[@itemprop='description']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath(".//span[@itemprop='description']/@id").string()
            if ssid:
                review.ssid = ssid.replace("fullReview-", "")
            else:
                review.ssid = review.digest()

        product.reviews.append(review)

    if product.reviews:
        session.emit(product)
