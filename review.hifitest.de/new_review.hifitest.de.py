from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.hifitest.de/testberichte'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "testOverviewPart")]')
    for rev in revs:
        title = rev.xpath('div[@class="testOverviewFac"]//text()').string(multiple=True)
        cats = rev.xpath('div[contains(@class, "testOverviewCat")]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cats=cats, url=url))

    next_url = data.xpath('//a[img[@alt="eine Seite vor"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Tech'

    if context.get('cats'):
        cats = context['cats'].split()
        cats_ = []
        for i, cat in enumerate(cats):
            if cat[0].isupper():
                cats_.append(cat)
            else:
                cats_[i-1] += ' ' + ' '.join(cats[i:])
                break

        product.category = '|'.join(cats_)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//tr[contains(., "Datum")]/td[not(contains(., "Datum"))]/text()').string()
    if date:
        review.date = date.split(',')[0]

    author = data.xpath('//tr[contains(., "Autor")]//a/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="testreviewContent"]//@alt').string()
    if grade_overall:
        grade_overall = grade_overall.split()[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//table[@class="fontSite18"]/tr')
    for grade in grades:
        grade_name = grade.xpath('td[1]/text()').string()
        grade_val = float(grade.xpath('.//@src').string().split('-')[-1].replace('.png', '')) / 2
        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    summary = data.xpath('//p[@class="introduction"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()|//h3[contains(., "Fazit")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="block-testbericht"]/p[not(@class)]|//div[@id="block-testbericht"]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)