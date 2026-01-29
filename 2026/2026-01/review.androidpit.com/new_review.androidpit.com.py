from agent import *
from models.products import *


XCAT = ['[video', 'video]', 'video review']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.nextpit.com/reviews/page/1'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not any(xcat in title.lower() for xcat in XCAT):
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()

    product.ssid = context['url'].split('/')[-1].replace('-review', '')

    product.name = data.xpath('//div[@class="deviceLinkText" or contains(@class, "__headline") or @class="np-product__header"]/*[self::h2 or self::h3 or self::span]/text()').string()
    if not product.name:
        product.name = context['title'].split('Durability test: ')[-1].split('[Test]')[-1].split(' test:')[0].split(' Test:')[-1].split(' First Look: ')[0].split('First Look: ')[-1].split(' Review: ')[0].split(' Review: ')[0].split(' Our Review of ')[0].split(' review: ')[0].split(' review: ')[0].split(' Retro-Review: ')[0].split(': hands-on review ')[0].replace('Hands-on review of the ', '').split(' review ')[0].split(' reviewed: ')[0].split(' tested: ')[0].split(' Tested: ')[0].replace(' A Long-Term Review', '').replace('[Hands-On User Review] ', '').replace('AndroidPIT Review Of ', '').replace(' Hands-On Review', '').replace('Testing the ', '').replace('Tested: ', '').replace("? Here's Our Review", '').split(' reviewed in ')[0].split(' re-reviewed: ')[0].split(' review, ')[0].replace(' Review', '').replace('Review of the ', '').replace(' hands-on review', '').replace(' review', '').replace('Hands on: ', '').strip()

    product.url = data.xpath('//span[contains(@class, "np-offer__link")]/@data-href').string()
    if not product.url:
        product.url = data.xpath('//a[@rel="sponsored"]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[@class="post-tag" and not(contains(., "Home") or contains(., "Manufac") or contains(., "More") or contains(., "Master your") or contains(., "Review"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="post-date"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author_name = data.xpath('//span[@class="post-author"]/a/text()').string()
    author_url = data.xpath('//span[@class="post-author"]/a/@href').string()
    if author_name and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
    elif author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

    pros = data.xpath('//h3[contains(., "Pros of")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip().strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[contains(., "Cons of")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip().strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-excerpt"]/p//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/following-sibling::p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h2[regexp:test(., "Conclusion|My Thoughts|Final Thoughts|Who should buy|Should You Buy|Final verdict", "i")])[last()]/following-sibling::p[not(contains(., "the device used in this review") or preceding-sibling::h2[contains(., "Where to Buy")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "Conclusion|My Thoughts|Final Thoughts|Who should buy|Should You Buy|Final verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post-content"]/p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
