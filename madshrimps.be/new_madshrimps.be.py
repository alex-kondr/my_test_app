from agent import *
from models.products import *


XCAT = ['Web News', 'Others']


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
    session.queue(Request('https://www.madshrimps.be/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="menu"]/li/a|//li[a[contains(., "Other")]]/ul[@class="sub-menu"]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True).replace('Expand', '').strip()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(@class, "entry-meta")]/span[@class="posted-on"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "entry-meta")]/span[@class="class="posted-by"]/span[@class="author vcard"]/a[not(contains(., "madshrimps team"))]/text()').string()
    author_url = data.xpath('//div[contains(@class, "entry-meta")]/span[@class="class="posted-by"]/span[@class="author vcard"]/a[not(contains(., "madshrimps team"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="title-entry-excerpt"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    context['excerpt'] = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)

    pages = data.xpath('(//form[@class="multipage-dropdown-form"])[1]//options')
    for page in pages:
        title = page.xpath('text()').string()
        url = page.xpath('@value')
        review.add_property(type="pages", value=dict(url=url, title=title))

    context['review'] = review
    context['product'] = product

    if pages:
        session.do(Request(url, use='curl', force_charset='utf-8'), process_review_last, dict(context, pages=True))
    else:
        process_review_last(data, context, session)


def process_review_last(data, context, session):
    strip_namespace(data)

    review = context['review']

    if context.get('pages'):
        conclusion = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
