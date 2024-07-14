from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gizguide.com/search/label/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@href, "reviews?updated-max=")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' - ')[0].split(', First ')[0].replace('Review', '').replace('Unboxing', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html' , '')
    product.category = 'Tecno'

    cats = data.xpath('//a[@rel="tag"]/text()[not(contains(., "reviews") or contains(., "tecno"))]').strings()
    if cats:
        product.category = '|'.join([cat.strip().title() for cat in cats])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//abbr[@class="published"]/@title').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/@title').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//span[b[contains(., "Pros")]]')
    for pro in pros:
        pro = pro.xpath('.//text()[not(contains(., "Pros"))]').string(multiple=True).strip(' -,')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[b[contains(., "Cons")]]')
    for con in cons:
        con = con.xpath('.//text()[not(contains(., "Cons"))]').string(multiple=True).strip(' -,')
        review.add_property(type='cons', value=con)

    summary = data.xpath('//b/span[@style="font-family: helvetica;"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Quick thoughts")]/following-sibling::div/span[not(.//i or contains(., "Update:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::div/span[not(.//i or contains(., "Update:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Quick thoughts")]/preceding-sibling::div[not(b/span)]/span[not(contains(., "See also:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding::div[@style and not(@class)]/span[not(.//i or @typeof or b[contains(., "Cons") or contains(., "Pros")] or contains(., "Update:") or contains(., "See also:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@style and not(@class)]/span[not(.//i or @typeof or b[contains(., "Cons") or contains(., "Pros")] or contains(., "Update:") or contains(., "See also:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
