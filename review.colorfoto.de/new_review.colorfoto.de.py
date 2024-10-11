from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.connect-living.de/testbericht/alle'), process_catlist, dict())


def process_catlist(data, context, session):
    arhivs = data.xpath('//a[@class="wkArchive__month"]')
    for arhiv in arhivs:
        url = arhiv.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//div[@class="wkTeaser__headlines"]/a')
    for prod in prods:
        title = prod.xpath('.//text()').string(multiple=True)

        if 'Archiv' not in title and 'Prime Day' not in title:
            url = prod.xpath('@href').string()
            session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):

    product = Product()
    product.name = context['title'].replace(' im Test', '').replace(' Test', '').replace('im Check', '').replace('Details', '').replace('als Download', '').replace('-Download', '').replace('- Download', '').replace('Download', '').replace('im Vergleich', '').split(':')[0].split(' - ')[0].strip()
    product.ssid = context['url'].split('-')[-1].replace('.html', '')

    product.category = data.xpath('//div[@class="weka_award__category"]/text()').string()
    if not product.category:
        product.category = 'Technik'

    product.url = data.xpath('//a[contains(@class, "wkSalesElement__button")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        if isinstance(prod_json, list):
            prod_json = prod_json[1]

            date = prod_json.get('datePublished')
            if date:
                review.date = date.split()[0]

    if not review.date:
        date = data.xpath('//p[contains(@class, "dateauthors")]/text()').string(multiple=True)
        if date:
            review.date = date.replace('Autor:', '').replace('•', '').strip()

    authors = data.xpath('//p[contains(@class, "dateauthors")]/strong/text()')
    for author in authors:
        author = author.xpath('text()').string()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "Rating--summary")]//span[contains(@class, "rating_percentage")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', '').replace(',', '.'))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    pros = data.xpath('//div[contains(@class, "Rating--pro")]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "Rating--contra")]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="wkArticlehead__intro"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    context['conclusion'] = data.xpath('//h2[not(@class)][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)
    if not context['conclusion']:
        context['conclusion'] = data.xpath('//h2[@class][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)

    context['excerpt'] = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p//text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[@class="maincol__contentwrapper"]/p//text()|//div[@class="maincol__contentwrapper"]/h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)

    context['product'] = product

    next_url = data.xpath('//a[contains(@class, "button--next")]/@href').string()
    if next_url:
        title = data.xpath('//h1[contains(@class, "headline")]/text()').string()
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
        title = data.xpath('//h1[contains(@class, "headline")]/text()').string()
        review.add_property(type='pages', value=dict(title=title + ' - page ' + str(page), url=data.response_url))

        conclusion = data.xpath('//h2[not(@class)][contains(text(), "Fazit") or contains(text(), "Testfazit")]/following-sibling::p[not(em)]//text()').string(multiple=True)
        if conclusion:
            context['conclusion'] = conclusion

        excerpt = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p//text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="maincol__contentwrapper"]/p//text()|//div[@class="maincol__contentwrapper"]/h2[not(contains(text(), "Benchmark")) and not(contains(text(), "Technische Details"))]//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[contains(@class, "button--next")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, page=page + 1))

    elif context['excerpt']:
        if context['conclusion']:
            review.add_property(type='conclusion', value=context['conclusion'])

        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
