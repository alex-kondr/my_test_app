from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://falkor-cda.bastian.globo.com/tenants/techtudo/instances/694b2dee-93a8-4065-ac90-41bca2dc88ce/posts/page/1'), process_revlist, {})


def process_revlist(data, context, session):
    revs = simplejson.loads(data.content).get('items', [])
    for rev in revs:
        title = rev.get('content', {}).get('title')
        prod_id = rev.get('id')
        date = rev.get('publication')
        url = rev.get('content', {}).get('url')
        session.queue(Request(url), process_review, dict(prod_id=prod_id, date=date, title=title, url=url))

    next_page = rev.get('nextPage')
    if next_page:
        session.queue(Request('https://falkor-cda.bastian.globo.com/tenants/techtudo/instances/694b2dee-93a8-4065-ac90-41bca2dc88ce/posts/page/' + str(next_page)), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.title = context['title'].replace('', '')
    product.url = context['url']
    product.ssid = context['prod_id']
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    if context['date']:
        review.date = context['date'].split('T')[0]

    author = data.xpath('//div[@class="content-publication-data__from"]//span/text()').string()
    author_url = data.xpath('//div[@class="content-publication-data__from"]//a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h2[@class="content-head__subtitle"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//p[contains(@class, "content-text__container") and not(contains(., "Canal do TechTudo") or contains(., "Fórum TechTudo"))]')
