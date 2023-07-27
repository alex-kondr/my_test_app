import simplejson

from agent import *
from models.products import *


URL = 'https://www.thegnet.org/blog-frontend-adapter-public/v1/post-list-widget/render-model?timezone=Europe/Zurich&postLimit=500&categoryId=87c39d34-b1fa-4ed1-abfe-580cd4b663bb'
OPTIONS = "-H 'instance: Y3LAmqqWxw9TTeqEw913q2ppHaajgDEA2S_QGLrMYWU.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTI2VDIxOjEwOjU4LjM4MVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiIzNzUwYzRhZC04YTEyLTQ2MzItYThmZi0zZDFjMDMzYjZkNzMiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ'"


def run(context, session):
    session.queue(Request(URL, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = simplejson.loads(data.content).get('posts', {}).get('body', [])

    for prod in prods:
        name = prod.get('title', '').replace('im Test', '').replace('The(G)net Review - ', '').replace(u'\u2019', "'").split(':', 1)
        name = name[1].strip() if len(name) > 1 else name[0].strip()
        url = prod.get('link')
        session.queue(Request(url, use='curl', max_age=0, force_charset='utf-8'), process_product, dict(name=name, url=url))


def process_product(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    author_url = ''
    date = ''
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        author_url = prod_json.get('author', {}).get('url')
        date = prod_json.get('datePublished', '').split('T')[0]

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = 'review'

    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.url = context['url']
    review.title = data.xpath('//title/text()').string()

    if date:
        review.date = date
    else:
        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

    summary = data.xpath('//div[@data-id="rich-content-viewer"]//p[@id="viewer-foo"]//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt_conclusion = data.xpath('//div[@data-id="rich-content-viewer"]//text()').string(multiple=True)
    if excerpt_conclusion:
        excerpt_conclusion = excerpt_conclusion.split('Fazit:')

        if len(excerpt_conclusion) > 1:
            conclusion = excerpt_conclusion[1].strip()
            review.add_property(type='conclusion', value=conclusion)

        excerpt = excerpt_conclusion[0]
        if summary:
            excerpt = excerpt.replace(summary, '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
