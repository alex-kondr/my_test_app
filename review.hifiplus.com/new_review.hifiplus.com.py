from agent import *
from models.products import *


XCAT = ['All Reviews']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://hifiplus.com/reviews/", use='curl'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(a, "Reviews")]/div/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()
        url = cat.xpath('.//a[contains(., "Overview")]/@href').string()
        if not url:
            url = cat.xpath('a/@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="content-box" and h3]')
    for rev in revs:
        title = rev.xpath('h3/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace(' review', '').replace(' Review', '').replace('Review ', '').strip()
    product.ssid = context['url'].strip('/').split('/')[-1]
    product.category = context['cat']

    product.url = data.xpath('//a[@data-wpel-link="external"][preceding-sibling::*[contains(., "Manufacturer")] or parent::*[preceding-sibling::*[contains(., "Manufacturer")]]]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//*[self::p or self::h3 or self::h4][contains(., "Manufacturer:") or regexp:test(., "Manufactur.* by:", "i")]/text()').string()
    if not manufacturer or not manufacturer.split(':')[-1].strip():
        manufacturer = data.xpath('//*[self::h3 or self::h4][contains(., "Manufacturer")]/following-sibling::p[normalize-space()][1]/text()').string()

    if manufacturer:
            product.manufacturer = manufacturer.split(':')[-1].strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('''//script[contains(., '"datePublished":"')]/text()''').string()
    if date:
        review.date = date.split('"datePublished":"')[-1].split('T', 1)[0]

    author = data.xpath('//ul[@class="detail-list"]/li/a[contains(@href, "author")]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.strip('/').split('/')[-1]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    conclusion = data.xpath('//div[@class="content-box"]//p[preceding::*[self::h3 or self::h4 or self::b][regexp:test(., "Final Thought|Conclusion", "i")]][normalize-space()][not(preceding::*[regexp:test(., "^\s*Technical specification|Learn more about|\s*Price and Contact Details|Final Thought", "i")])][not(regexp:test(., "^\s*Price and Contact Details|Learn more about", "i"))]//text()').string(multiple=True)
    if conclusion and conclusion.strip():
        review.add_property(type='conclusion', value=conclusion.strip())

    excerpt = data.xpath('//div[@class="content-box"]//p[not(preceding::*[regexp:test(., "^\s*Technical specification|Learn more about|\s*Price and Contact Details|Final Thought|Conclusion", "i")])][not(regexp:test(., "^\s*Price and Contact Details|Learn more about|Conclusion", "i"))]//text()').string(multiple=True)
    if excerpt and excerpt.strip():
        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
