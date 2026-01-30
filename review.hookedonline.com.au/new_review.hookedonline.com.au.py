from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request("https://www.hookedonline.com.au/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "Products")]//ul[@class="level_1"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        cats1 = cat.xpath('.//ul[contains(@class, "first-col")]/li')
        for cat1 in cats1:
            cat1_name = cat1.xpath('a/text()').string()

            subcats = cat1.xpath('ul/li/a')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string()
                    url = subcat.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
            else:
                url = cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="wrapper-thumbnail col-xs-6 col-sm-4 col-lg-3"]/div/div/h3//a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//i[@class="fa fa-chevron-right"]/parent::a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('|Other Boating', '')
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()
    product.sku = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.ssid = product.sku

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_count = data.xpath('//span[@itemprop="ratingCount"]//text()').string()
    if not revs_count or revs_count == "0":
        return
    
    revs = data.xpath('//head/meta[@itemprop="itemReviewed"]/parent::*')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('(following-sibling::body//h4)[1]//text()').string()
        review.date = rev.xpath('following-sibling::head/meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('(following-sibling::body//span[@itemprop="author"])[1]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::head/meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('(following-sibling::body//span[@itemprop="description"])[1]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if author:
                review.ssid = review.digest()
            else:
                review.ssid = review.digest(excerpt)
            
            product.reviews.append(review)
        
    if product.reviews:
        session.emit(product)
