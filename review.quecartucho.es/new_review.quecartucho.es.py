from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://quecartucho.es/blog/todos-los-review-de-impresoras-analizadas/'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="pt-cv-ifield"]//h2//a[contains(@href, "review-del-experto")]') #149
    for prod in prods:
        title = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(title=title, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].replace('|', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = '|'.join(data.xpath('//li/a[@rel="category tag"]/text()').strings())

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

    pros = data.xpath('//span[contains(@id, "_Lo_mejor")]/following::ul[1]/li')
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@id="_Lo_peor"]/following::ul[1]/li')
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            review.add_property(type='cons', value=con)

    # conclusion = data.xpath('//h2[.//strong[contains(., "Opinión y valoraciones") or contains(., "Impresión y valoración")]]/following::p[not(@class or @style or a[contains(@href, "soporte")] or .//a[@class="rank-math-link"] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or contains(., "el precio puede variar"))]//text()').string(multiple=True)
    conclusion = data.xpath('(//h2[.//strong[contains(., "Opinión y valoraciones") or contains(., "Impresión y valoración")]]/following-sibling::p[not(@class or @style or a[contains(@href, "soporte")] or .//a[@class="rank-math-link"] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or contains(., "el precio puede variar"))]|//h2[.//strong[contains(., "Opinión y valoraciones") or contains(., "Impresión y valoración")]]/following-sibling::div[contains(@class, "wp-block-column")]//p)//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    manual_url = data.xpath('//a[@download="download"]/@href').string()
    if manual_url:
        product.add_property(type='link.manufacturer.userguide', value=dict(url=manual_url, title='Manual'))

    excerpt = data.xpath('//h2[.//strong[contains(., "Opinión y valoraciones") or contains(., "Impresión y valoración")]]/preceding::p[not(@class or @style or strong[contains(., "Descripción")] or a[contains(@href, "soporte")] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or .//strong[contains(., "Ventajas")] or .//strong[contains(., "Desventajas")] or contains(., "el precio puede variar") or contains(., "Precio por copia"))]//text()').string(multiple=True)
    # if not excerpt:
    #     excerpt = data.xpath('').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
