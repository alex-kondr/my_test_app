from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://stereonet.com/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    if revs:
        offset = context.get('offset', 0) + 12
        options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://stereonet.com/reviews' -H 'X-Requested-With: XMLHttpRequest' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=0' -H 'TE: trailers'"
        next_url = 'https://stereonet.com/page_templates/article_list_ajax/reviews/' + str(offset)
        session.queue(Request(next_url, use='curl', options=options, max_age=0), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    title = data.xpath('//h1[@class="h1"]/text()').string()
    if not title:
        return

    product = Product()
    product.name = title.replace('Review of ', '').replace('Review: ', '').replace('REVIEW: ', '').replace(' Review', '').replace(' REVIEW', '').replace(' review', '').replace('EXCLUSIVE:', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath('//div[contains(@class, "brand")]/h2/a/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="postedDate"]/span/text()').string()
    if date:
        review.date = date.replace('Posted on', '').strip()

    author =data.xpath('//div[@class="textholder"]/h5/a/text()').string()
    author_url = data.xpath('//div[@class="textholder"]/h5/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "summary")]/p[not(contains(., "Posted in") or contains(., "£"))]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")]|//h3[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")])/following-sibling::p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")]|//h3[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")])/preceding-sibling::p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="thumbnails"]/p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
