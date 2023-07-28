import simplejson

from agent import *
from models.products import *


URL = 'https://www.thegnet.org/blog-frontend-adapter-public/v1/post-list-widget/render-model?timezone=Europe/Zurich&postLimit=500&categoryId=87c39d34-b1fa-4ed1-abfe-580cd4b663bb'
OPTIONS = "-H 'instance: k2jeapWFnMu4uhCAePqM5dtjUD9kQt0Nfy5M-C7mkVE.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTI4VDA3OjQ0OjExLjE2MVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiI2MjJkNjU4My0wZGE4LTRlMTYtOGExZi04OWYyMGJmYTM0M2MiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ'"


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

    summary = data.xpath('//div[@data-id="rich-content-viewer"]//p[@id="viewer-foo"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = ''
    conclusion = ''
    is_conclusion = False
    excerpt_conclusion = data.xpath('//div[@data-id="rich-content-viewer"]/div/*[not(@id="viewer-foo")]')
    for exc_con in excerpt_conclusion:
        grade_img = exc_con.xpath('.//div[@data-hook="imageViewer"][not(.//path|.//span)]/@class').string()
        if grade_img:
            break

        text = exc_con.xpath('.//text()').string(multiple=True)
        if text:
            if 'Fazit:' in text:
                is_conclusion = True
                continue
            if is_conclusion:
                conclusion += ' ' + text
            else:
                excerpt += ' ' + text

    if excerpt:
        review.add_property(type='excerpt', value=excerpt.strip())

    if conclusion:
        review.add_property(type='conclusion', value=conclusion.strip())

    if excerpt or conclusion:
        product.reviews.append(review)

        session.emit(product)
