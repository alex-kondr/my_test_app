from agent import *
from models.products import *
import re

def run(context, session):
    session.browser.agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    session.sessionbreakers = [SessionBreak(max_requests=30000)]
    session.queue(Request('http://www.sweetwater.com'), process_first_page, {})

def process_first_page(data, context, session):
    for link in data.xpath('//ul[@class="cats"]//div[@class="submenu"]//li//a[text()][not(@class)]'):
        url=link.xpath('@href').string()
        category=link.xpath('text()').string()
        if url and category:
            session.queue(Request(url),process_category,dict(category=category))

def process_category(data, context, session):
    if data.xpath('//div[@class="products"]//div[@class="product-card"]'):
        process_product_list(data, context, session)
        return

    for link in data.xpath('//div[@filtertype="category"]//a'):
        url = link.xpath('@href').string()
        category = link.xpath('descendant::text()').string()
        if url and category:
            category = context['category'] + ' | ' + category
            session.queue(Request(url),process_category,dict(category=category))

def process_product_list(data, context, session):
    for link in data.xpath('//div[@class="products"]//div[@class="product-card"][descendant::span[@class="rating__stars"]]//h2//a'):
        url = link.xpath('@href').string()
        name = link.xpath('descendant::text()').string(multiple=True)
        if url and name:
            session.queue(Request(url), process_product, dict(context, url=url,name=name))

    next = data.xpath('//a[@class="next"]//@href').string()
    if next:
        session.queue(Request(next), process_product_list, dict(context))

def process_product(data, context, session):
    product=Product()
    product.name=context['name']
    product.url=context['url']
    product.ssid=product.name + product.url
    product.category=context['category']
    product.manufacturer=''

    sku = data.xpath('//td[@itemprop="mpn"]//text()').string()
    if sku:
        product.properties.append(ProductProperty(name="Manufacturer Part Number", type="id.manufacturer", value= sku))

    rurl = data.xpath('//a[@class="product-meta__rating"]//@href').string()
    if rurl:
        session.do(Request(rurl), process_reviews, dict(context, product=product, rurl=rurl))

    if product.reviews:
        session.emit(product)

def process_reviews(data, context, session):
    product = context['product']

    c=0
    for link in data.xpath('//body[descendant::node()[regexp:test(name(),"h\d")][@itemprop="author"]]'):
        c += 1
        review=Review()
        review.product=product.name
        review.url=context['rurl']
        review.ssid=product.ssid + ' review ' + str(c)
        review.type='user'

        # Title
        title = link.xpath('following-sibling::body[1]/descendant::node()[regexp:test(name(),"h\d")][@itemprop="name"]//text()').string()
        if title:
            review.title = title

        # Publish date
        pub_date=link.xpath('following-sibling::head[1]/descendant::meta[@itemprop="datePublished"]//@content').string()
        if pub_date:
            review.date=pub_date
        else:
            review.date='unknown'

        # Author
        author=link.xpath('descendant::node()[regexp:test(name(),"h\d")][@itemprop="author"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            review.authors.append(Person(name='unknown', ssid='unknown'))

        # Grades
        overall=link.xpath('descendant::span[@class="rating-stars"]//@data-rating').string()
        if overall:
            review.grades.append(Grade(name='Overall Rating', type='overall', value=overall, best=5))

        # Summary
        summary=link.xpath('following-sibling::body[1]/descendant::p[@itemprop="description"]//text()').string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary',value=summary))

        product.reviews.append(review)
