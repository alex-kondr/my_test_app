from agent import *
from models.products import *


XTITLE = ['IFA ', 'SPECIAL: ']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.areadvd.de/tests/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//p[contains(., "Tests nach Rubriken")]/following-sibling::ul[1]/li[@class="list-posts"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('(//div[@id="rechts"]|//div[@id="rechts"]//strong|//div[@class="list-posts"])/a[not(img or contains(., "Weiter") or ancestor::div[@class="navigation"])]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not any(title.startswith(xtitle) for xtitle in XTITLE) and 'TEST:' in title or 'review' in title.lower():
            session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//div[@class="navigation"]/div[@class="alignleft"]//a').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('TEST: ', '').replace('VIDEO-REVIEW: ', '').replace('REVIEW: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('test-', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="postdate"]/text()').string()
    if author:
        author = author.split(' ', 1)[-1].strip()
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//*[regexp:test(name(), "^h\d$") and contains(., "Fazit")]/following-sibling::p[not(contains(., "Datum: "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//*[regexp:test(name(), "^h\d$") and contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry"]/p[not(contains(., "Datum: "))]//text()').string(multiple=True)

    pages = data.xpath('//center/*[self::span or self::a][contains(@class, "post-page-numbers")]')
    if pages:
        for page in pages:
            title = review.title + ' Pagina - ' + page.xpath('text()').string()
            url = page.xpath('@href').string() or data.response_url
            review.add_property(type='pages', value=dict(title=title, url=url))

        session.do(Request(url), process_review_next, dict(product=product, review=review, excerpt=excerpt))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    review = context['review']

    conclusion = data.xpath('//*[regexp:test(name(), "^h\d$") and contains(., "Fazit")]/following-sibling::p[not(contains(., "Datum: "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//*[regexp:test(name(), "^h\d$") and contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[@class="entry"]/p[not(contains(., "Datum: "))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
