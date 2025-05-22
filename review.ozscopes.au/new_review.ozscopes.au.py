from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.ozscopes.com.au/'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True)

        sub_cats = cat.xpath('.//ul/li[contains(@class, "level1")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('.//ul/li[contains(@class, "level2")]/a')
            for sub_cat1 in sub_cats1:
                sub_nbame1 = sub_cat1.xpath('//text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()

                session.queue(Request(url), process_category, dict(context, url=url, cat=name))


def process_category(data, context, session):
    prods = data.xpath("//li[@class='item product product-item']")
    for prod in prods:
        url = prod.xpath(".//strong/a/@href").string()
        title = prod.xpath(".//strong/a//text()").string()
        revs = prod.xpath(".//div[@class='reviews-actions']/a//text()").string()
        if revs:
            session.queue(Request(url), process_product, dict(context, url=url, title=title))
    
    nexturl = data.xpath("//li[@class='item pages-item-next']/a[@class='action next']/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = data.xpath("//div/@data-product-id").string()
    product.category = context['cat']
    product.url = context['url']
    product.sku = data.xpath("//td[@data-th='Barcode']//text()").string()

    revsurl = 'https://www.ozscopes.com.au/review/product/listAjax/id/' + product.ssid
    session.do(Request(revsurl), process_reviews, dict(context, product=product))
    
    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session): 
    product = context['product']

    revs = data.xpath("//li[@class='item review-item']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        
        grade_overall = rev.xpath(".//div[@class='rating-result']/@title").string()
        if grade_overall:
            grade_overall = grade_overall.split('%')[0]
            review.grades.append(Grade(type='overall', value=float(int(grade_overall)/20), best=5.0))
        
        review.title = rev.xpath(".//div[@class='review-title']//text()").string()
    
        for body in rev.xpath("ancestor::body/following-sibling::body"):
            excerpt = body.xpath(".//div[@itemprop='description']//text()").string(multiple=True)
            if excerpt:
                review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            author_name = body.xpath(".//strong[@itemprop='author']//text()").string()
            if author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

            date = body.xpath(".//time/@datetime").string()
            if date:
                review.date = date

            if excerpt or author_name or date:
                break

            grade_name = body.xpath(".//span[@class='label rating-label']//text()").string()
            grade_val = body.xpath(".//div[@class='rating-result']/@title").string().replace('%', '')
            review.grades.append(Grade(name=grade_name, value=float(int(grade_val)/20), best=5.0))

        review.ssid = product.ssid + '-' + review.date + '-' + author_name
        product.reviews.append(review)

    nexturl = data.xpath("//li[@class='item pages-item-next']/a/@href").string()
    if nexturl:
        session.do(Request(nexturl), process_reviews, dict(context, product=product))


