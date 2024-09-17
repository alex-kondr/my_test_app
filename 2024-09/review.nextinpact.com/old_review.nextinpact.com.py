from agent import *
from models.products import *


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='article']/h2/a")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    nexturl = data.xpath("//a[@class='next-page']")
    if nexturl:
        page = int(context['page']) + 1
        nexturl = 'https://www.nextinpact.com/t/tests/' + str(page)
        session.queue(Request(nexturl), process_prodlist, dict(context, page=page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].split(":")[0]
    product.ssid = context['url'].split('/')[-1]
    product.url = context['url']
    product.category = data.xpath("//div[contains(@class, 'badge-container')]/a[1]//text()").string() or 'Tests'

    review = Review()
    review.title = context['name']
    review.date = data.xpath("//meta[@name='article:published_time']/@content").string().split("T")[0]
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    
    author_name = data.xpath("//meta[@name='author']/@content").string(multiple=True)
    if author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))
    
    summary = data.xpath("//p[@class='actu_chapeau']//text()").string(multiple=True)
    if not summary:
        summary = data.xpath("//div[@id='article-content']//div[@id='headlines-container']//p//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))
    
    excerpt = data.xpath("//div[@id='article-content']//p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary,'')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if excerpt or summary:
        product.reviews.append(review)
        session.emit(product)


def run(context, session): 
    session.queue(Request('https://www.nextinpact.com/t/tests'), process_prodlist, dict(page=1))
