from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.daisybeauty.com/recensioner/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[contains(@class, "next")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].rsplit(' – ', 1)[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Skönhetsprodukter'

    cats = data.xpath('//a[contains(@href, "/makeup/")]/text()').join('/')
    if cats:
        product.category += '|' + cats

    product.url = data.xpath('//a[regexp:test(text(), "du hittar den här|finns bland annat här")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//p[time[@class="entry-time"]]/text()').string(multiple=True)

    grade_overall = data.xpath('//a[contains(@href, "/betyg/")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[contains(@class, "ingress")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="post-container"]/p[not(contains(@class, "meta"))]//text()').string(multiple=True)
    if excerpt:
        if 'Slutsats:' in excerpt:
            excerpt, conclusion = excerpt.rsplit('Slutsats:', 1)
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
