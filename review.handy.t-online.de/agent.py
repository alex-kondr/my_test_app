from agent import *
from models.products import *


XCAT = ['Aktuelles', 'Weltall', 'WhatsApp', 'Windows', 'Kreuzworträtsel']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.t-online.de/digital/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@data-testid]/h3/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@data-tb-title="true"]/a[@data-tb-link="true"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[.//img[@title="Nächste Seite"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Passwort-Test: ', '').split(' im Test – ')[0].split(' im Test: ')[0].split(' im Vorab-Test: ')[0].replace('Test: ', '').replace(' im Test', '').replace(' im Praxistest', '').replace(' im Doppel-Test', '').replace(' im Alltagstest', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('id_', '')
    product.category = context['cat'].replace('Tests', 'Technik')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@data-tb-author and not(contains(., "t-online"))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@data-testid, "ArticleBody")]/div/div/p[contains(@class, "font-bold")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@data-testid="StageLayout.StreamItem"]/p[not(contains(@class, "font-bold"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
