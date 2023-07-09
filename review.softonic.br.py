import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.softonic.com.br'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="menu-categories__list"]/li')
    for cat in cats:
        name = cat.xpath('button[@class="menu-categories__link js-toggle"]/span//text()').string()

        subcats = cat.xpath('.//li[not(.//div)]/a')
        for subcat in subcats:
            subcat_name = subcat.xpath("text()").string()
            url = subcat.xpath('@href').string() + ':data/1'
            session.queue(Request(url), process_category, dict(cat=name+"|"+subcat_name, url=url))


def process_category(data, context, session):
    prods = data.xpath('//li[@class="apps-list__item"]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="app-info__name"]//text()').string()
        url = prod.xpath('.//a[contains(@class, "app-info")]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    page_numbers = data.xpath('//a[@class="s-pagination__link"]//text()').strings()
    current_page_number = int(context['url'].split('/')[-1])
    next_page_number = current_page_number + 1
    if str(next_page_number) in page_numbers:
        next_url = context['url'].replace('/' + str(current_page_number), '/' + str(next_page_number))
        session.queue(Request(next_url), process_category, dict(context, url=next_url))
        
        
def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('//script[contains(text(), "applicationCategory")]//text()').string())

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json.get('author', {}).get('name')
    product.ssid = data.xpath('//meta[@name="appId"]/@content').string()
    
    review = Review()
    review.type = "pro"
    review.url = product.url
    review.date = prod_json.get('dateModified')
    
    author = prod_json.get('review', {}).get('author', {}).get('name')
    if author:
        review.authors.append(Person(name=author, ssid=author))
        
    pros = prod_json.get('review', {}).get('positiveNotes', {}).get('itemListElement', {})
    for pro in pros:
        pro = pro.get('name')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = prod_json.get('review', {}).get('negativeNotes', {}).get('itemListElement', {})
    for con in cons:
        con = con.get('name')
        if con:
            review.add_property(type='cons', value=con)
            
    grade_overall = prod_json.get('aggregateRating', {}).get('ratingValue')
    if grade_overall and grade_overall > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
            
    excerpt = prod_json.get('review', {}).get('reviewBody')
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
        review.ssid = review.digest() if author else review.digest(excerpt)
        product.reviews.append(review)
        session.emit(product)

    # revs = data.xpath('//ul[@class="row list-users-comments"]')
    # if revs:
    #     revs_url = context['url'] + '/comentarios-participantes'
    #     session.queue(Request(revs_url), process_reviews, dict(product=product))
        
        
# def process_reviews(data, context, session):
#     product = context['product']

#     revs = data.xpath('//ul[@class="post-list top-bar"]/li[@class="post"]')
#     for rev in revs:
#         review = Review()
#         review.type = "user"
#         review.url = product.url

#         author = rev.xpath('.//span[@class="author publisher-anchor-color"]//text()').string()
#         if author:
#             review.authors.append(Person(name=author, ssid=author))        

#         excerpt = rev.xpath('.//div[@class="post-message"]//text()').string()
#         if excerpt:
#             review.add_property(type='excerpt', value=excerpt)
#             review.ssid = review.digest() if author else review.digest(excerpt)
#             product.reviews.append(review)

#     # next_url = data.xpath('//div[@class="cms-page--reviews__pagination"]//a[@title="next"]/@href').string()
#     # if next_url:
#     #     session.queue(Request(next_url), process_reviews, dict(context, product=product))

#     if product.reviews:
#         session.emit(product)
