from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://geekweek.interia.pl/testy", use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "ids-card")]')
    for rev in revs:
        title = rev.xpath('article/@title').string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('- test')[0].split('- pierwsze wrażenia')[0].split('Sprawdzamy ')[-1].split(': Test')[0].split('Test: ')[-1].split('Test -')[-1].split('Test faceta: ')[-1].split('Test Faceta: ')[-1].split('Test ')[-1].replace("Testowałam", "").replace("TEST", "").replace("Recenzja", "").replace("Test", "").replace("[]", "").strip()
    product.url = context["url"]
    product.ssid = product.url.split(',')[-1]

    product.category = data.xpath('(//a[contains(@class, "box__link")])[last()][not(regexp:test(., "Technologia|Testy"))]/text()').string()
    if not product.category:
        product.category = 'Technologia'

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[contains(@class, "author")]/a/text()').string()
    author_url = data.xpath('//p[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('#')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[contains(@class, "ids-paragraph--lead")]//text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[*[regexp:test(., "Czy warto kupić|Podsumowanie", "i")]]/following-sibling::div/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[*[regexp:test(., "Czy warto kupić|Podsumowanie", "i")]]/preceding-sibling::div/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class or @id)]/div/p//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
