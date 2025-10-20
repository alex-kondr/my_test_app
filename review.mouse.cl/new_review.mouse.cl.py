from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.latercera.com/pf/api/v3/content/fetch/story-feed-tag-fetch?query={"feedOffset":0,"feedSize":12,"fromComponent":"result-list","tagSlug":"review"}&d=1070&mxId=00000000&_website=la-tercera', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('content_elements', [])
    for rev in revs:
        title = rev.get('headlines', {}).get('basic')
        url = 'https://www.latercera.com' + rev.get('canonical_url')
        session.queue(Request(url), process_review, dict(title=title, url=url))

    offset = context.get('offset', 0) + 12
    revs_cnt = int(revs_json.get('count', 0))
    if offset < revs_cnt:
        next_url = 'https://www.latercera.com/pf/api/v3/content/fetch/story-feed-tag-fetch?query={"feedOffset":' + str(offset) + ',"feedSize":12,"fromComponent":"result-list","tagSlug":"review"}&d=1070&mxId=00000000&_website=la-tercera'
        session.queue(Request(next_url, max_age=0), process_revlist, dict(offset=offset))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('Reseña | ', '').replace('Review |', '').replace('Review| ', '').replace('Review: ', '').replace('Review ', '').replace(u'\L', '').replace(u'  ', '').strip(' |')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = data.xpath('//div[contains(@class, "heading")]/span[contains(@class, "section__name")]//text()').string(multiple=True)

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\L', '').replace(u'  ', '').strip()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    author = data.xpath('//a[contains(@class, "author")]/text()').string()
    if not author:
        author = data.xpath('//meta[@name="author"]/@content').string()

    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[regexp:test(text(), "Nota:.+⭐")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.count('⭐')
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//h2[contains(@class, "subtitle") and not(contains(., "⭐"))]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Veredict", "i")]/following-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Veredict", "i")]/preceding-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
