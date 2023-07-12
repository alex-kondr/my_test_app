from agent import *
from models.products import *


XCAT = ["Offers", "Brands", "Customer Service", "Corporate Info"]
PAGE = '?pageNumber='


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.andertons.co.uk/sitemap'), process_frontpage, dict())


def process_frontpage(data, context, session):
    page_num = '1'
    cats1 = data.xpath("//div[@class='dtb-sitemap__segment-content']")
    for cat1 in cats1:
        cat1_name = cat1.xpath('.//a[@aria-level="2"]/text()').string()
        if cat1_name in XCAT:
            continue
        
        cats2 = cat1.xpath('.//li[@class="h2 dtb-sitemap__segment-subtitle"]')
        if cats2:
            for cat2 in cats2:
                cat2_name = cat2.xpath('a[@aria-level="3"]/text()').string()
                
                cats3 = cat2.xpath('.//li[@class="h3"]/a')
                if cats3:
                    for cat3 in cats3:
                        cat3_name = cat3.xpath("text()").string()
                        url = cat3.xpath("@href").string()
                        if url:
                            session.queue(Request(url + PAGE + page_num), process_category, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name, page_num=page_num))
                else:
                    url = cat2.xpath('a[@aria-level="3"]/@href').string()
                    if url:
                        session.queue(Request(url + PAGE + page_num), process_category, dict(cat=cat1_name+'|'+cat2_name, page_num=page_num))
                
        else:
            url = cat1.xpath('.//a[@aria-level="2"]/@href').string()
            if url:
                session.queue(Request(url + PAGE + page_num), process_category, dict(cat=cat1_name, page_num=page_num))
        

def process_category(data, context, session):
    prods = data.xpath('//div[@class="c-product-grid"]//div[@class="o-tile"]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "o-tile__row o-tile__title")]/h4/text()').string()
        url = prod.xpath('.//a[@class="o-tile__link"]/@href').string()

        revs = prod.xpath('.//div[@class="o-tile__row o-tile__reviews"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
            
    prod_count = data.xpath('//div[@class="flex-groww"]/p/text()').string()
    if not prod_count:
        return
    prod_count = prod_count.split(' - ')[1].split(' of ')
    if prod_count[0] != prod_count[1]:
        next_page_num = str(int(context['page_num']) + 1)
        session.queue(Request(data.response_url.replace(PAGE+context['page_num'], PAGE+next_page_num)), process_category, dict(context, page_num=next_page_num))
        
        
def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.add_property(type='id.manufacturer', value=product.ssid)

    revs = data.xpath('//div[@class="o-customer-review"]')
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//span[@class="o-customer-review__date"]/text()').string()

        author_name = rev.xpath('.//p[@class="o-customer-review__name"]/span/text()').string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath('.//div[@class="o-review-stars"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.xpath('.//p[@class="o-customer-review__rating"]/span')
        if grades:
            for grade in grades:
                name_value = grade.xpath("text()").string()
                if name_value:
                   name = name_value.split(" ")[0]
                   value = float(name_value.split(" ")[1])
                   review.grades.append(Grade(name=name, value=value, best=5.0))
                else:
                    continue

        excerpt = rev.xpath('text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
