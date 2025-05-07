from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.telepolis.pl/api/infinity-content/artykuly/testy-sprzetu?page=1', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    data_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(data_json.get('contents'))
    revs = new_data.xpath('//a[contains(@class, "teaser--mobile")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    has_next_page = data_json.get('hasNextPage')
    if has_next_page:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.telepolis.pl/api/infinity-content/artykuly/testy-sprzetu?page=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = title.replace('(pierwsze wrażenia)', '').replace('(test)', '').replace('(Test)', '').replace('- test', '').replace('(albo zazdrosna)', '').split('. Test')[-1].split('? Test')[-1].strip()
    product.ssid = context['url'].split('/')[-1].replace('testy-', '')
    product.category = 'Technologia'

    product.url = data.xapth('//a[@class="sales-item"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    revs_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if revs_json:
        revs_json = simplejson.loads(revs_json)

        date = revs_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "date__name")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="article__lead"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "content")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
