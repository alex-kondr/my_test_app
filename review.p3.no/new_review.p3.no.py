from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.nrk.no/anmeldelser/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//h3[contains(@class, "title")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@data-id and not(preceding::button[contains(., "Vis flere")]) and figure]')
    if not revs:
        return

    for rev in revs:
        ssid = rev.xpath('@data-id').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, url=url, ssid=ssid))

    if context.get('next_url'):
        offset = context.get('offset', 9) + 9
        next_url = context['next_url'].split('.offset=')[0] + '.offset=' + str(offset) + '&' + context['next_url'].split('.offset=')[-1].split('&', 1)[-1]
        session.queue(Request(next_url), process_revlist, dict(context, offset=offset))

    else:
        next_url = data.xpath('//button[contains(@class, "page-forward") and not(preceding::button[contains(., "Vis flere")])]/@data-id[contains(., "size=18")]').string()
        if next_url:
            next_url = 'https://www.nrk.no/serum/api/render/' + next_url
            session.queue(Request(next_url), process_revlist, dict(context, next_url=next_url))


def process_review(data, context, session):
    if data.xpath('//img[contains(@alt, "1 tall")]'):
        return  # Multi-revs. There full reviews for any product on site

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = context['ssid']

    name = data.xpath('//div[@class="review-info"]/h3/text()').string()
    if name:
        product.name = name.strip('« »')
    else:
        product.name = title

    product.category = context['cat']
    genres = data.xpath('//p[contains(text(), "Sjanger:")]/text()').string()
    if genres:
        product.category += '|' + genres.title().replace('Sjanger:', '').strip().replace(', ', '/')

    manufacturer = data.xpath('//p[contains(text(), "Distributør:")]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('Distributør:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author_url = data.xpath('//a[@class="author__name"]/@href').string()
    author = data.xpath('//a[@class="author__name"]/text()').string()
    if not author:
        author = data.xpath('//div[contains(@class, "name")]/text()').string()

    if author and author_url:
        author_ssid = author_url.split('-')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="review-rating"]/span/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split()[-1]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    summary = data.xpath('//div[contains(@class, "article-lead")]/p/text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3|//h5)[contains(., "Konklusjon")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class,"article-body")]/p[not(preceding-sibling::h2[regexp:test(.,"Konklusjon")])][not(contains(., "(Anmeldelsen fortsetter under bildet)") or regexp:test(., "anmeldelse:", "i"))]//text()[not(contains(., "[youtube"))][not(parent::strong) and not(contains(text(), "Spoileradvarsel!") or contains(., "href="))]').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
