from agent import *
from models.products import *


CATS = ['Medieafspiller', 'Lyd og andet tilbehør', 'Smart Home']


def run(context, session):
    session.queue(Request('https://digitalt.tv/kategori/anmeldelser/', force_charset='utf-8', use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@class="post-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8', use='curl', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Test: ', '').split(' – ')[0].split(': Test')[0].replace(' Test', '').replace(' test', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    cat = data.xpath('//a[contains(@class, "post-cat")]/text()').string()
    if cat and cat in CATS:
        product.category = cat
    else:
        product.category = 'Tech'

    ean = data.xpath('//tr[contains(., "EAN ")]/td[not(contains(., "EAN "))]/text()').string()
    if ean and ean.isdigit() and len(ean) > 9:
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    if author:
        author = author.split(' - ')[-1].strip()
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[contains(@class, "plus")]//li')
    if not pros:
        pros = data.xpath('//div[contains(@class, "thumbup")]//li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "minus")]//li')
    if not cons:
        cons = data.xpath('//div[contains(@class, "thumbdown")]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//a[contains(@href, "wp-content/uploads") and regexp:test(@href, "anbefaling|godt-koeb")]')
    if is_recommended:
        review.add_property(value=True, type='is_recommended')

    summary = data.xpath('//h2[@class="entry-sub-title"]//text()').string(multiple=True)
    if summary:
        summary = summary.strip(' -+*')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Konklusion")]/following-sibling::p[not(a[contains(@href, "pricerunner.dk")])]//text()|//h2[contains(., "Konklusion")]/following-sibling::text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Konklusion")]/preceding-sibling::p[not(a[contains(@href, "pricerunner.dk")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(a[contains(@href, "pricerunner.dk")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
