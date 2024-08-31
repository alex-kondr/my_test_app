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
    if data.xpath('count(//p[strong[contains(., "Fazit:")]])') > 1:
        process_reviews(data, context, session)
        return

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

    summary = data.xpath('//p[@class="Template-INTRO"]//text()').string(multiple=True)
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


def process_reviews(data, context, session):
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
        review.date = data.xpath('//div[@class="Template-ARTIKEL-DATUM"]/text()').string()

        author = data.xpath('//meta[@name="author"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={i} and contains(., "positiv auf:") and not(contains(., "Preis") or contains(., "Mehr Info") or @class)]//text()'.format(i=i*2)).string(multiple=True)
        if pros:
            pros = pros.split('positiv auf:')[-1].split('.')
            for pro in pros:
                pro = pro.strip()
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro.strip())

        cons = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={i} and contains(., "negativ auf:") and not(contains(., "Preis") or contains(., "Mehr Info") or @class)]//text()'.format(i=i*2)).string(multiple=True)
        if cons:
            cons = cons.split('negativ auf:')[-1].split('.')
            for con in cons:
                con = con.strip()
                if len(con) > 1:
                    review.add_property(type='cons', value=con.strip())

        summary = data.xpath('//p[@class="Template-INTRO"]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={i} and contains(., "Gerät und Handhabung:") and not(contains(., "Mehr Info") or @class)]//text()[not(contains(., "Preis"))]'.format(i=i*2)).string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('Gerät und Handhabung:', '').strip()
            review.add_property(type='excerpt', value=excerpt)

        conclusion = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={i} and contains(., "Fazit:") and not(contains(., "Preis") or contains(., "Mehr Info") or @class)]//text()'.format(i=i*2)).string(multiple=True)
        if conclusion:
            conclusion = conclusion.replace('Fazit:', '').strip()
            review.add_property(type='conclusion', value=conclusion.strip())

            product.reviews.append(review)

            session.emit(product)

