from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.campgarden.de/cg/pages/69092/geraete'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="Internal-block"]/div[@class="Internal-Name"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    date = data.xpath('//div[@class="Template-ARTIKEL-DATUM"]/text()').string()
    author = data.xpath('//meta[@name="author"]/@content').string()
    summary = data.xpath('//p[@class="Template-INTRO"]//text()').string(multiple=True)

    if data.xpath('count(//p[strong[contains(., "Fazit:")]])') > 1:
        revs = data.xpath('//h3[@class="Template-ZTITEL" and not(strong)]')
        for i, rev in enumerate(revs, start=1):
            product = Product()
            product.name = rev.xpath('text()').string()
            product.url = context['url']
            product.ssid = product.url.split('/')[-2]
            product.category = 'Tech'

            review = Review()
            review.type = 'pro'
            review.title = context['title']
            review.url = product.url
            review.ssid = product.ssid
            review.date = date

            if author:
                review.authors.append(Person(name=author, ssid=author))

            if summary:
                review.add_property(type='summary', value=summary)

            excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={i} and not(contains(., "Preis") or contains(., "Mehr Info") or @class)]//text()'.format(i=i*2)).string(multiple=True)
            if excerpt:
                excerpt, conclusion = excerpt.split('Fazit:')

                review.add_property(type='excerpt', value=excerpt.strip())

                review.add_property(type='conclusion', value=conclusion.strip())

                product.reviews.append(review)

                session.emit(product)

    else:
        product = Product()
        product.name = context['title'].split(' - ')[0].replace('im Test', '').replace('-Langzeittest', '').replace('-Test', '').replace(' Test', '').strip()
        product.url = context['url']
        product.ssid = product.url.split('/')[-2]
        product.category = 'Tech'

        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.url = product.url
        review.ssid = product.ssid
        review.date = data.xpath('//div[@class="Template-ARTIKEL-DATUM"]/text()').string()

        author = data.xpath('//meta[@name="author"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = data.xpath('//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[contains(@class, "Artikel")]/p[not(@class or .//*[contains(@class, "INLINE")] or preceding-sibling::h4)]//text()').string(multiple=True)

        conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::p[not(preceding-sibling::h4)]//text()').string(multiple=True)
        if not conclusion:
            if 'Das Fazit der Redaktion ist eindeutig:' in excerpt:
                excerpt, conclusion = excerpt.split('Das Fazit der Redaktion ist eindeutig:')
            elif 'Unser Fazit:' in excerpt:
                excerpt, conclusion = excerpt.split('Unser Fazit:')

        if excerpt:
            review.add_property(type='excerpt', value=excerpt.strip())

        if conclusion:
            review.add_property(type='conclusion', value=conclusion.strip())

            product.reviews.append(review)

            session.emit(product)
