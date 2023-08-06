import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.connect-living.de/testbericht/'), process_catlist, dict())
    session.queue(Request('https://www.connect-living.de/testbericht/alle'), process_catlist_arhiv, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="crosslinks__element"]/a')
    for cat in cats:
        name = data.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_catlist_arhiv(data, context, session):
    arhivs = data.xpath('//a[@class="teaser__link"][not(@tabindex)]')
    for arhiv in arhivs:
        url = arhiv.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//h3[@class="teaser__headline"]/a')
    for prod in prods:
        title = prod.xpath('text()').string()

        if 'Archiv' not in title and 'Prime Day' not in title:
            url = prod.xpath('@href').string()
            session.queue(Request(url), process_review, dict(context, url=url, title=title))


def process_review(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        if isinstance(prod_json, list):
            prod_json = prod_json[1]

    product = Product()
    product.name = context['title'].replace(' im Test', '').replace(' Test', '').replace('im Check', '').replace('Details', '').replace('als Download', '').replace('-Download', '').replace('- Download', '').replace('Download', '').replace('im Vergleich', '').split(':')[0].split(' - ')[0].strip()
    product.ssid = context['url'].split('-')[-1].replace('.html', '')

    product.category = context.get('cat')
    if not product.category:
        product.category = data.xpath('(//li[@class="breadcrumb__element"]//span)[last()]/text()').string().replace('Tests', 'Technik')

    product.url = data.xpath('//h3[contains(text(), "Tipp")]/following-sibling::p/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = "pro"
    review.ssid = product.ssid
    review.url = context['url']
    review.title = context['title']

    date = prod_json.get('datePublished')
    if not date:
        date = data.xpath('//p[@class="articlehead__dateauthors"]/text()').string()
    if date:
        review.date = date.split()[0]

    authors = data.xpath('//p[@class="articlehead__dateauthors"]/strong')
    for author in authors:
        author = author.xpath('text()').string()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('(//div[@class="inline_rating__result inline_rating__result--starpercent"]/text())[last()]').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', '').replace(',', '.'))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    summary = data.xpath('//p[@class="articlehead__lead"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//li[span[@class="fas fa-plus-circle"]][normalize-space(.)]')
    for pro in pros:
        pro = pro.xpath('text()').string()
        review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//li[span[@class="fas fa-minus-circle"]][normalize-space(.)]')
    for con in cons:
        con = con.xpath('text()').string()
        review.properties.append(ReviewProperty(type='cons', value=con))

    context['conclusion'] = data.xpath('//h2[not(@class)][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)
    if not context['conclusion']:
        context['conclusion'] = data.xpath('//h2[@class][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)

    context['excerpt'] = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p//text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[@class="maincol__contentwrapper"]/p//text()|//div[@class="maincol__contentwrapper"]/h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)

    context['product'] = product

    next_url = data.xpath('//a[@class="next pagination__button pagination__button--next"]/@href').string()
    if next_url:
        title = data.xpath('//span[@class="tableofcontents__link tableofcontents__link--highlight"]/text()').string()
        review.add_property(type='pages', value=dict(title=title + ' - page 1', url=data.response_url))
        session.do(Request(next_url), process_review_next, dict(context, review=review, page=2))

    else:
        context['review'] = review
        context['page'] = 1
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context['page']
    if page > 1:
        title = data.xpath('//span[@class="tableofcontents__link tableofcontents__link--highlight"]/text()').string()
        review.add_property(type='pages', value=dict(title=title + ' - page ' + str(page), url=data.response_url))

        conclusion = data.xpath('//h2[not(@class)][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)
        if conclusion:
            context['conclusion'] = conclusion

        excerpt = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p//text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="maincol__contentwrapper"]/p//text()|//div[@class="maincol__contentwrapper"]/h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[@class="next pagination__button pagination__button--next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, page=page + 1))

    elif context['excerpt']:
        if context['conclusion']:
            review.add_property(type='conclusion', value=context['conclusion'])

        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
