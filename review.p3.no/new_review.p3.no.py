from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.nrk.no/anmeldelser/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@data-testid and a and .//h2]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    revs_json = data.xpath('//astro-island/@props[contains(., "initialCursor")]').string()
    try:
        cursor = simplejson.loads(revs_json).get('initialCursor')[-1]

        if cursor:
            next_url = 'https://www.nrk.no/komponenter/api/autonomous-content/plugs.json?type=reviews&count=6&cursor=' + cursor
            session.queue(Request(next_url), process_revlist_next, dict())
    except:
        pass


def process_revlist_next(data: Response, context: dict[str, str], session: Session):
    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('plugs', [])
    for rev in revs:
        url = rev.get('url')
        session.queue(Request(url), process_review, dict(url=url))

    next_page = revs_json.get('hasNextPage')
    if next_page is True:
        cursor = revs_json.get('cursor')
        next_url = 'https://www.nrk.no/komponenter/api/autonomous-content/plugs.json?type=reviews&count=6&cursor=' + cursor
        session.queue(Request(next_url), process_revlist_next, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    if data.xpath('//img[contains(@alt, "1 tall")]|//h2[@class="numbered-heading"]'):
        return  # Multi-revs. There full reviews for any product on site

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = data.xpath('//div[@data-content-element="ReviewType"]/a[contains(@href, "?type=")]/text()').string() or 'Teknologi'

    name = data.xpath('//h2[@class="font-700"]/text()').string()
    if name:
        product.name = name.strip('« »')
    else:
        product.name = title

    genres = data.xpath('//div[h2[@class="font-700"]]/p/text()').string()
    if genres:
        product.category += '|' + genres.title().replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@itemprop="name"]/text()').string()
    author_url = data.xpath('//a[span[@itemprop="name"]]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('-')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    rev_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    try:
        grade_overall = simplejson.loads(rev_json).get('reviewRating', {}).get('ratingValue')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0, worst=1.0))
    except:
        pass

    summary = data.xpath('//p[contains(@class, "article__lead")]//text()').string(multiple=True)
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
