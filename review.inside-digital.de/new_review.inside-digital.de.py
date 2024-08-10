from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.inside-digital.de/thema/test'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "td_module_11")]')
    for rev in revs:
        title = rev.xpath('div[contains(@class, "td-module-title")]//a/text()').string()
        cats = rev.xpath('.//a[@class="td-post-category"]/text()').string()
        url = rev.xpath('div[contains(@class, "td-module-title")]//a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cats=cats, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' im Test:')[0].split(' Test:')[0].replace(' im Test', '').strip()
    product.url = context['url'].replace('/test', '')
    product.ssid = product.url.split('/')[-1].replace('-im-test', '')
    product.category = 'Tech'

    if context['cats']:
        product.category = '|'.join([cat.capitalize() for cat in context['cats'].split(', ')])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="fn"]/a/text()').string()
    author_url = data.xpath('//span[@class="fn"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[contains(., "Vorteile")]|//h2[contains(., "Pros")])/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Nachteile")]|//h2[contains(., "Contras")])/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(@id, "fazit")]/following-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or preceding-sibling::ul)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(@id, "fazit")]/preceding-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or preceding-sibling::ul)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)