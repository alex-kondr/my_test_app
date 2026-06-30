from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://quecartucho.es/blog/todos-los-review-de-impresoras-analizadas/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    # no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('|')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = "Impresoras"

    product.url = data.xpath('//a[contains(@href, "amzn.to")]/@href').string()
    if not product.url:
        product.url = context['url']

    mpn = data.xpath('//li[contains(., "SKU")]/text()|//a[contains(@href, "sku=")]/@href').string()
    if mpn:
        mpn = mpn.split('=')[-1].split(':')[-1].split(',')[0].split()[-1].split('(')[0].replace(')', '').strip()
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//li[contains(., "Código de barras")]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.type = 'pro'
    review.ssid = product.ssid
    review.date = data.xpath('//li[@class="meta date posted-on nv-show-updated"]/text()|//time[@class="entry-date published"]/@content').string()

    author = data.xpath('//span[@class="author-name fn"]/a[@rel="author"]/text()').string()
    author_url = data.xpath('//span[@class="author-name fn"]/a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//span[contains(@id, "_Lo_mejor")]/following::ul[1]/li')
    if not pros:
        pros = data.xpath('//span[contains(@id, "_Lo_mejor")]/following::ol[not(@class)]/li[not(@id or @class or preceding::h2[contains(., "Related Posts:")])]')

    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(@id, "_Lo_peor")]/following::ul[1]/li')
    if not cons:
        cons = data.xpath('//span[contains(@id, "_Lo_peor")]/following::ol[not(@class)]/li[not(@id or @class or preceding::h2[contains(., "Related Posts:")])]')

    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2[contains(., "Opinión y valoraci") or contains(., "Impresión y valoración")]/following-sibling::p[not(@class or @style or a[contains(@href, "soporte")] or .//a[@class="rank-math-link"] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or contains(., "el precio puede variar"))]|//h2[.//strong[contains(., "Opinión y valoraciones") or contains(., "Impresión y valoración")]]/following-sibling::div[contains(@class, "wp-block-column")]//p|//h2[.//strong[contains(., "Opinión y valoraci") or contains(., "Impresión y valoración")]]/following-sibling::ul)//text()[not(contains(., "brother.com") or contains(., "brother.es") or contains(., "hp.com") or contains(., "epson.es") or contains(., "canon.es") or contains(., "Pros:") or contains(., "Cons:"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//span[contains(@id, "_Lo_mejor")]/preceding::p[not(@class or @style or strong[contains(., "Descripción")] or a[contains(@href, "soporte")] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or .//strong[contains(., "Ventajas")] or .//strong[contains(., "Desventajas")] or contains(., "el precio puede variar") or contains(., "Precio por copia"))]//text()[not(contains(., "brother.com") or contains(., "brother.es") or contains(., "hp.com") or contains(., "epson.es") or contains(., "canon.es") or contains(., "Pros:") or contains(., "Cons:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Opinión y valoraci") or contains(., "Impresión y valoración")]/preceding::p[not(@class or @style or strong[contains(., "Descripción")] or a[contains(@href, "soporte")] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or .//strong[contains(., "Ventajas")] or .//strong[contains(., "Desventajas")] or contains(., "el precio puede variar") or contains(., "Precio por copia"))]//text()[not(contains(., "brother.com") or contains(., "brother.es") or contains(., "hp.com") or contains(., "epson.es") or contains(., "canon.es") or contains(., "Pros:") or contains(., "Cons:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h2/following-sibling::div[@class="aawp" or @class="wp-block-embed__wrapper"])[1]/following-sibling::p[not(@class or @style or strong[contains(., "Descripción")] or a[contains(@href, "soporte")] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or .//strong[contains(., "Ventajas")] or .//strong[contains(., "Desventajas")] or contains(., "el precio puede variar") or contains(., "Precio por copia") or contains(., "drivers"))]//text()[not(contains(., "brother.com") or contains(., "brother.es") or contains(., "hp.com") or contains(., "epson.es") or contains(., "canon.es") or contains(., "Pros:") or contains(., "Cons:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2/following-sibling::p[not(@class or @style or strong[contains(., "Descripción")] or a[contains(@href, "soporte")] or .//a[@rel="nofollow"] or strong[contains(., "Opiniones")] or .//strong[contains(., "Ventajas")] or .//strong[contains(., "Desventajas")] or contains(., "el precio puede variar") or contains(., "Precio por copia") or contains(., "drivers"))]//text()[not(contains(., "brother.com") or contains(., "brother.es") or contains(., "hp.com") or contains(., "epson.es") or contains(., "canon.es") or contains(., "Pros:") or contains(., "Cons:"))]').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
