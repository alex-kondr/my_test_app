import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.connect-living.de/testbericht/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="crosslinks__element"]/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict())

    session.queue(Request('https://www.connect-living.de/testbericht/alle'), process_prodlist_arhiv, dict())


def process_prodlist_arhiv(data, context, session):
    arhivs = data.xpath('//a[@class="teaser__link"][not(@tabindex)]')
    for arhiv in arhivs:
        url = arhiv.xpath('@href').string()
        session.queue(Request(url), process_prodlist_arhiv, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="teaser__headline"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()

        if 'Archiv' not in name and 'Prime Day' not in name:
            url = prod.xpath('@href').string()
            session.queue(Request(url), process_product, dict(context, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@class="articlehead__headline"]/text()').string().replace('im Test:', '').replace('im Test', '').replace(' Test:', '').replace(' Test', '').replace('im Check', '').replace('Details', '').replace('als Download', '').replace('-Download', '').replace('- Download', '').replace('Download', '').replace('im Vergleich', '')
    product.url = data.xpath('//h3[contains(text(), "Tipp")]/following-sibling::p/a/@href').string() or context['url']
    product.category = data.xpath('(//li[@class="breadcrumb__element"]//span)[last()]/text()').string()
    product.ssid = context['url'].split('-')[-1].replace('.html', '')

    context['product'] = product

    process_review(data, context, session)


def process_review(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        if isinstance(prod_json, list):
            prod_json = prod_json[1]

    product = context['product']

    review = Review()
    review.type = "pro"
    review.url = context['url']

    date = prod_json.get('datePublished')
    if date:
        review.date = date.split()[0]
    else:
        date = data.xpath('//p[@class="articlehead__dateauthors"]/text()').string()
        if date:
            review.date = date.split()[0]

    authors = prod_json.get('author', {})
    if isinstance(authors, list):
        for author in authors:
            author = author.get('name')
            if author:
                review.authors.append(Person(name=author, ssid=author))
    elif authors:
        author = authors.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))
    else:
        authors = data.xpath('//p[@class="articlehead__dateauthors"]/strong')
        for author in authors:
            author = author.xpath('text()').string()
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = prod_json.get('mentions', {}).get('review', {}).get('reviewRating', {}).get('ratingValue')
    bestRating = prod_json.get('mentions', {}).get('review', {}).get('reviewRating', {}).get('bestRating')
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', '').replace(',', '.'))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=float(bestRating)))

    summary = prod_json.get('description')
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//li[span[@class="fas fa-plus-circle"]]')
    if pros:
        for pro in pros:
            pro = pro.xpath('text()').string()
            review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//li[span[@class="fas fa-minus-circle"]]')
    if cons:
        for con in cons:
            con = con.xpath('text()').string()
            review.properties.append(ReviewProperty(type='cons', value=con))

    conclusion = data.xpath('//h2[contains(text(), "Fazit")]/following-sibling::p/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p//text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2//text()').string(multiple=True) or data.xpath('//div[@class="maincol__contentwrapper"]/p//text()|//div[@class="maincol__contentwrapper"]/h2//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        review.ssid = product.ssid

        product.reviews.append(review)

    next_url = data.xpath('//a[@class="next pagination__button pagination__button--next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_review, dict(product=product, url=next_url))

    elif product.reviews:
        session.emit(product)
