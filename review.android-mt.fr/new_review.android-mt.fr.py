from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://android-mt.ouest-france.fr/category/appareil/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = product.url.split('/')[-2]
    product.category = 'Technique'

    product.name = data.xpath('//div[@class="column"]/h2/text()').string()
    if not product.name:
        product.name = context['title'].replace('Promo et test de', '').replace('Test Express :', '').replace('Test de', '').replace('Test du', '').split(':')[0]

    product.url = data.xpath('//a[contains(., "Découvrir l’offre")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author-name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    # grade # .//div[@class="note-labo"]/following-sibling::div

    summary = data.xpath('//div[@class="excerpt"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[contains(., "verdict")]]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "verdict")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="pub_pave_article2"]/following-sibling::p[not(strong[contains(., "verdict")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
