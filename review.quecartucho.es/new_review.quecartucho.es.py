from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://quecartucho.es/blog/todos-los-review-de-impresoras-analizadas/'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="pt-cv-ifield"]//h2//a[contains(@href, "review-del-experto")]')
    for prod in prods:
        title = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(title=title, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].replace('|', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    # product.category = data.xpath('//li/a[@rel="category tag"][1]/text()').string()

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid
    review.date = data.xpath('//li[@class="meta date posted-on nv-show-updated"]/text()').string()

    author = data.xpath('.//span[@class="author-name fn"]/a[@rel="author"]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    summary = data.xpath('//h2/following-sibling::div[1][@class="aawp"]/preceding-sibling::p[not(strong[contains(., "Descripción")])]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//span[@id="_Lo_mejor"]/following::ul[1]/li')
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@id="_Lo_peor"]/following::ul[1]/li')
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[.//strong[contains(., "Opinión y valoraciones")]]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conslusion', value=conclusion)

    excerpt = data.xpath('//div[@class="nv-content-wrap entry-content"]//h2/following-sibling::*//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
