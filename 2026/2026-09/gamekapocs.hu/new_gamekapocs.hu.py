from agent import *
from models.products import *
import simplejson
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.gamekapocs.hu/cikkek', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[@class="page-item active"]/following-sibling::li[1]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' teszt')[0].replace('...', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Játékok'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    try:
        rev_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
        date = simplejson.loads(rev_json).get('datePublished')
        if date:
            review.date = date.split('T')[0]
    except:
        pass

    date = data.xpath('//div[@class="byline-meta"]/span/text()').string()
    if date and not review.date:
        review.date = date.rsplit('. ', 1)[0].strip()

    author = data.xpath('//a[@class="byline-author"]/text()').string()
    author_url = data.xpath('//a[@class="byline-author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="rating-score-value"]/text()').string()
    if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[contains(@class, "list--pros")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace('<br />', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@class, "list--cons")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace('<br />', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="article-lead"]//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).replace('&#8211;', '-').replace('&#8222;', '"').replace('&#8221;', '"').replace('&#8230;', '...').replace('&#8217;', "'").replace('&otilde;', '').replace(u'�', '').strip()
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="article-body"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).replace('&#8211;', '-').replace('&#8222;', '"').replace('&#8221;', '"').replace('&#8230;', '...').replace('&#8217;', "'").replace('&otilde;', '').replace(u'�', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
