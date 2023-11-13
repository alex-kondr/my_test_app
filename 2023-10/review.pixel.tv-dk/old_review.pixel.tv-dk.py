from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.pixel.tv/programserie/ingame/'), process_revlist, dict())


def process_revlist(data, context, session):
    for prod in data.xpath("//h2"):
        name = prod.xpath(".//a/text()").string()
        url = prod.xpath(".//a/@href").string()
        date = prod.xpath("following-sibling::p[1]/time/@datetime").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url, date=date))

    next_page = data.xpath("//a[@class='fPaginationNext']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    try:
        data.xpath("/")
    except:
        return

    product = Product()
    product.name = context['name'].replace('Anmeldelse: ', '').replace('anmeldelse', '')
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = "Review"

    review = Review()
    review.title = context['name']
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date'].split("T")[0]

    author_name = data.xpath("//h3[contains(.,'Værter')]/following-sibling::ul//a/text()").string()
    author_url = data.xpath("//h3[contains(.,'Værter')]/following-sibling::ul//a/@href").string()
    if author_name and author_url:
        review.authors.append(Person(name=author_name, ssid=author_name, url=author_url))

    excerpt = data.xpath("(//div[@class='fContent'])[1]/p//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)
        session.emit(product)
