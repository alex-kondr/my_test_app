from agent import *
from models.products import *
import simplejson


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://gadzetomania.pl/gadzety,temat,6008941124117121'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[@class="wp-link" and @id]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        ssid = rev.xpath('@id').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url, ssid=ssid))

    next_url = data.xpath('//a[@data-pagination="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('TEST ', '').replace('Test ', '').replace('[TEST]', '').replace('[test]', '').replace('(test)', '').split(' - test ')[0].strip()
    product.url = context['url']
    product.ssid = context['ssid']
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

    author_url = data.xpath('//a[contains(@href, ",autor,")]/@href').string()
    author = data.xpath('//div[contains(@class, "article-author")]//text()').string(multiple=True)
    if not author and rev_info_json:
        author = rev_info_json.get('author', [{}])[0].get('name')

    if author and author_url:
        author_ssid = author_url.split('?')[0].split(',')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "article-lead")]/p[not(@class)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "content-text")]/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').replace(u'\x98', '').replace(u'', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
