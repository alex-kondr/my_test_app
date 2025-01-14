from agent import *
from models.products import *
debug = True


def process_frontpage(data, context, session):
    prods = data.xpath("//div[@id='container']//a[@class='art_titl']")
    for prod in prods:
        url = prod.xpath("@href").string()
        name = prod.xpath(".//text()").string()
        session.queue(Request(url), process_product, dict(url=url, name=name))

    nexturl = data.xpath("//div[@id='paginare']/a[@class='selected']/following-sibling::a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_frontpage, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath("(//ul[@id='navi']/li/a)[last()]//text()").string()
    product.url = context['url']

    review = Review()
    review.title = context['url']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    author_date = data.xpath("//span[@class='art_info']//text()").string().split('|')
    review.date = author_date[1].strip()
    author = author_date[0].strip().replace('de ', '')
    review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath("(//div[@id='continut_articol']//p//strong)[1]").string(multiple=True)
    review.properties.append(ReviewProperty(type='summary', value=summary))

    pages = data.xpath("//div[@id='paginare']/a[@class='selected']/following-sibling::a")
    if pages:
        for page in pages:
            page_url = page.xpath("@href").string()
            page_title = review.title + ' - ' + page.xpath(".//text()").string()
            review.properties.append(ReviewProperty(type='pages', value={'url': page_url, 'title': page_title}))
        session.queue(Request(page_url), process_product_lastpage, dict(product=product, review=review))
    else:
        excerpt = data.xpath("//div[@id='continut_articol']//p//text()").string(multiple=True)
        if summary in excerpt:
            excerpt = excerpt.replace(summary, '')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    product.reviews.append(review)
    session.emit(product)


def process_product_lastpage(data, context, session):
    review = context['review']

    conclusion = data.xpath("//div[@id='continut_articol']//p//text()").string(multiple=True)
    review.properties.append(ReviewProperty(type='conclusion', value=conclusion))


def run(context, session): 
    session.queue(Request('http://www.hit.ro/review'), process_frontpage, {})
