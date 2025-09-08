from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.queue(Request('https://www.fotografie.nl/boeken/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revlist = data.xpath("//div[@class='dynamic-item w-dyn-item']")
    for rev in revlist:
        title = rev.xpath("a[@class='post-title']/text()").string()
        url = rev.xpath("a[@class='post-title']/@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-1]
    product.category = 'Boeken'

    product.url = data.xpath('//a[contains(., "Bestel dit boek")]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//p[contains(., "Uitgever:")]/text()[contains(., "Uitgever:")]').string()
    if manufacturer:
        product.manufacturer = h.unescape(manufacturer).replace('Uitgever:', '').replace('&Amp;', '&').strip()

    ean = data.xpath('//p[contains(., "ISBN:")]//text()[contains(., "ISBN:")]').string(multiple=True)
    if ean:
        ean = ean.replace('ISBN:', '').strip()
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="date"]/text()').string()

    author = data.xpath('//div[contains(@class, "by-author")]/div[contains(@class, "author-div")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "author-div")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('''//div[contains(@class, "rich-text")]/p[not(regexp:test(., "Pagina's:|Uitgever:|Vertaling:|ISBN:"))]//text()''').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
