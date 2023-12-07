from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://quecartucho.es/blog/todos-los-review-de-impresoras-analizadas/'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="pt-cv-ifield"]//h2//a[contains(@href, "review-del-experto")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace('| Review del Experto', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//li/a[@rel="category tag"][1]/text()').string()

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid
    review.date = data.xpath('//li[@class="meta date posted-on nv-show-updated"]/text()').string()

    author = data.xpath('.//span[@class="author-name fn"]/a[@rel="author"]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    excerpt = data.xpath('//div[@class="nv-content-wrap entry-content"]//h2/following-sibling::*//text()').string(multiple=True)#//h2/following-sibling::p[count(preceding-sibling::div)=1]

    for pro in data.xpath('//span[@id="_Lo_mejor"]/../following-sibling::ul[1]/li'):
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            review.properties.append(ReviewProperty(type='pros', value=pro))
            excerpt = excerpt.replace(pro, '')

    for con in data.xpath('.//span[@id="_Lo_peor"]/../following-sibling::ul[1]/li'):
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            review.properties.append(ReviewProperty(type='cons', value=con))
            excerpt = excerpt.replace(con, '')

    remove_from_excerpt = data.xpath("//div[@class='aawp']//span[contains(text(), 'Oferta')]/../..//text()").string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//span[@id="_Principales_caracteristicas"]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//span[@id="_Principales_caracteristicas"]/../following-sibling::ul[1]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//span[@id="_Principales_caracteristicas"]/../following-sibling::p[1]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//ul[@class="blocks-gallery-grid"]//li//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//table[@class="aawp-table"]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    excerpt = excerpt.replace('Ofertas para comprar:', '')
    remove_from_excerpt = data.xpath('//span[@id="_Ofertas_para_comprar"]/../following-sibling::div[1]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//div[@class="aawp"]//div[@class="aawp-grid aawp-grid--col-3"]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//div[@class="aawp"]//div[@class="aawp-grid aawp-grid--col-3"]/../following-sibling::p[1]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//div[@class="aawp"]//div[@class="aawp-grid aawp-grid--col-3"]/../following-sibling::div[1]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//span[contains(@id, "_Opiniones_")]/..//following-sibling::div[@class="aawp"][following::figure]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    # remove_from_excerpt = data.xpath('//div[@class="aawp"]//div[@class="aawp-grid aawp-grid--col-3"]/../following-sibling::*[following::*[child::span[contains(@id, "Recomendamos")]]//text()').string(multiple=True)
    # if remove_from_excerpt:
    #     excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath("//span[contains(@id, '_Unboxing_')]/..//text()").string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath('//span[contains(@id, "_Unboxing_")]/..//following-sibling::*[following::div[@class="abh_text"]]//text()').string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath("//span[contains(@id, 'Ficha_tecnica')]/..//text()").string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    remove_from_excerpt = data.xpath("//span[contains(@id, 'Ficha_tecnica')]/..//following-sibling::*[following::*[@id='_Principales_caracteristicas']]//text()").string(multiple=True)
    if remove_from_excerpt:
        excerpt = excerpt.replace(remove_from_excerpt, '')

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
