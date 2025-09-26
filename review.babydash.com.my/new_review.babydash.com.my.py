from agent import *
from models.products import *


XCAT = ['Gifts', 'Sale', 'Brands', 'Formula & Food', 'View Brands']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.babydash.com.my/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//div[@class='top-container']/ol/li//a")
    for cat in cats:
        name = cat.xpath(".//text()").string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//dl[dt[contains(., "Category")]]//ol[@class="items"]/li')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('span//a/text()').string()

        if sub_name not in XCAT:
            sub_cats1 = sub_cat.xpath('ol/li//a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()
                if sub_name1 not in XCAT:
                    if sub_name1 != sub_name:
                        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+sub_name+'|'+sub_name1))
                    else:
                        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//a[@class='product-item-link']")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//a[@class='link next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.sku = data.xpath("//div[@itemprop='sku']//text()").string()
    product.ssid = data.xpath("//div[@class='product-info-price']/div/@data-product-id").string()
    product.category = context['cat']
    product.url = context['url']

    revs_cnt = data.xpath("//span[@itemprop='reviewCount']/text()").string()
    if revs_cnt:
        reviews_url = "https://www.babydash.com.my/review/product/listAjax/id/" + str(product.ssid)
        session.do(Request(reviews_url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context["product"]

    revs = data.xpath("//div[@class='review-content']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath("following-sibling::div/p[@class='review-date']/time/@datetime").string()

        author = rev.xpath("following-sibling::div/p[@class='review-author']/strong/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.xpath("preceding-sibling::span/span/text()").string()
        if grade:
            grade = int(grade.replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=grade, best=5))

        grades = rev.xpath('//div[@itemprop="reviewRating"]').string()
        if grade_q:
            name = 'span/span/text()'
            'div/@title'
            grade_q = int(grade_q.replace('%', '')) / 20
            review.grades.append(Grade(name='Quality', value=grade_q, best=5))

        title = rev.xpath("parent::body/preceding-sibling::body[3]//li[@itemscope='itemscope']/div[@class='review-title']/text()").string()
        excerpt = rev.xpath("text()").string()
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
