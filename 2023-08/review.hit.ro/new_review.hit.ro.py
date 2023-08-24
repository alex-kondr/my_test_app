from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.hit.ro/gadgeturi.html'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@class="mdl-button mdl-js-button mdl-button--raised mdl-button--accent"]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat='Gadgeturi|' + name))


def process_revlist(data, context, session):
    prods = data.xpath('//div[@class="mdl-card__title"]/a')
    for prod in prods:
        title = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[i[text()="skip_next"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Preview:', '').replace('(Consumer Preview)', '').split('Passport:')[0].replace('Test Drive:', '').replace('Test-soc:', '').replace('Teste:', '').replace('Review HIT.ro:', '').replace('(Review)', '').split('- REVIEW')[0].replace(' REVIEW','').replace('- Preview', '').replace('Preview ', '').replace('(Video)', '').replace('(VIDEO)', '').replace('- VIDEO', '').replace('(foto&video)', '').replace('(review)', '').replace('(teste)', '').replace(' TEST', '').replace('Zvon:', '').replace('￢', '').replace(', in teste', '').replace('- mini review', '').split('- REVIEW')[0].split('- VEZI VIDEO')[0].split(', video review')[0].split('- Video Review')[0].split('- Review video')[0].split(', preview')[0].split('- trailer')[0].split('PureView -')[0].split('PureView, ')[0].split('cu Pureview')[0].split(' PureView')[0].replace(' preview', '').replace('Review ', '').strip()
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('--')[-1].replace('.html', '')

    review = Review()
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//span[@class="mdl-chip__text"]/text()').string()
    if date:
        review.date = date.split(',')[0]

    summary = data.xpath('//div[contains(@class, "supporting-text-body")]//p/b[1]/text()[string-length() > 5]').string()
    summary2 = data.xpath('((//div[contains(@class, "supporting-text-body")]//strong)[2]|//div[br]/b/strong)/text()[string-length() > 11]').string(multiple=True)
    if not summary:
        summary = data.xpath('((//div[contains(@class, "supporting-text-body")]//strong)[1]|//div[br]/b/strong)/text()[string-length() > 11]').string(multiple=True)
    if summary and summary2:
        summary2 = summary + ' ' + summary2

    excerpt = data.xpath('(//div[br]|//p[br]|//div[br]/b|//div[br]/strong|//div[br]/b/strong)/text()[string-length() > 18 and not(contains(., "\\")) and not(contains(., "Sursa:")) and not(contains(., "*")) and not(contains(., "Surse:")) and not(contains(., "Detalii Rail Nation")) and not(contains(., "Toți jucătorii care")) and not(contains(., "Accesati Forumul oficial")) and not(contains(., "Jucătorii care cumpară")) and not(contains(., "Trailer:")) and not(contains(., "precum:"))]|//u[text()="Specificații"]/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[br]/div|//p[br]|//div[br]/b|//div[br]/strong)/text()[string-length() > 18 and not(contains(., "\\")) and not(contains(., "Sursa:")) and not(contains(., "Surse:"))]').string(multiple=True)
    if not excerpt and summary:
        excerpt = data.xpath('(//div[contains(@class, "supporting-text-body")]//strong)[position() > 1]/text()').string(multiple=True)
    elif not excerpt:
        excerpt = data.xpath('//div[contains(@class, "supporting-text-body")]//strong/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "supporting-text-body")]/span//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "supporting-text-body")]//span//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "supporting-text-body")]//font[not(contains(., "Sursa:")) and not(contains(., "Surse:"))]//text()').string(multiple=True)

    if excerpt:
        if summary2 and excerpt.startswith(summary2):
            review.add_property(type='summary', value=summary2)
            excerpt = excerpt.replace(summary2, '')
        elif summary and excerpt.startswith(summary):
            review.add_property(type='summary', value=summary)
            excerpt = excerpt.replace(summary, '')

        excerpt = excerpt.split('Specificații')[0].split('Specificatii ')[0].strip()

        if len(excerpt) > 30:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
