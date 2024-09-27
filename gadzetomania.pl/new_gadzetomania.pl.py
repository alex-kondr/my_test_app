from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://gadzetomania.pl/gadzety,temat,6008941124117121'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="prev" and contains(@href, "strona=")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('TEST ', '').replace('Test ', '').replace('[TEST]', '').replace('[test]', '').replace('(test)', '').split(' - test ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split(',')[-1]
    product.category = 'Gadżety'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_info_json = data.xpath('//script[contains(., "datePublished")]/text()').string()
    if rev_info_json:
        rev_info_json = simplejson.loads(rev_info_json)

    date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if not date and rev_info_json:
        date = rev_info_json.get('datePublished')

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, ",autor,")]/text()').string()
    if not author and rev_info_json:
        author = rev_info_json.get('author', [{}])[0].get('name')

    if author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="VXd-"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
