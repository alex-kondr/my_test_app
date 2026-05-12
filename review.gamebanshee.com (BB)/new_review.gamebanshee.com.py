from agent import *
from models.products import *


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
    session.queue(Request('http://www.gamebanshee.com/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//tr[contains(@class, "cat-list")]')
    for rev in revs:
        title = rev.xpath('td[contains(@class, "title")]/a/text()').string()
        date = rev.xpath('td[contains(@class, "date")]/text()').string()
        author = rev.xpath('td[contains(@class, "author")]/text()').string()
        url = rev.xpath('td[contains(@class, "title")]/a/@href').string()
        session.queue(Request(url.replace('.html', '/all-pages.html')), process_review, dict(title=title, url=url, author=author, date=date))

    next_url = data.xpath('//li[contains(@class, "next")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]

    product.category = data.xpath('//dl[contains(text(), "Category")]/a[not(contains(text(), "Reviews"))]/text()').string()
    if not product.category:
        product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    author = context['author']
    if author:
        author = author.replace('Written by ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//article/p//text()[preceding::*[contains(., "Conclusion")]]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    pages = data.xpath('//div[h3[contains(., "Article Index")]]/ul/li/a[not(contains(., "All Pages"))]')
    for page in pages:
        title = page.xpath('text()').string()
        url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))

    excerpt = data.xpath('//article/p//text()[not(preceding::*[contains(., "Conclusion")] or contains(., "Conclusion"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
