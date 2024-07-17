from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.stereonet.com/uk/page_templates/article_list_ajax/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@itemprop="name"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    if revs:
        offset = context.get('offset', 0) + 12
        next_url = 'https://www.stereonet.com/uk/page_templates/article_list_ajax/reviews/' + str(offset)
        session.queue(Request(next_url), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review of ', '').replace('Review: ', '').replace('REVIEW: ', '').replace(' Review', '').replace(' REVIEW', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath('//h4[@class="zone-title"]/following-sibling::ul//@alt').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="posted-date"]/span/text()').string()
    if date:
        review.date = date.replace('Posted on', '').strip()

    author =data.xpath('//div[@class="textholder"]/h3/a/text()').string()
    author_url = data.xpath('//div[@class="textholder"]/h3/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="summary"]/p[not(contains(., "Posted in") or contains(., "£"))]//text()').string(multiple=True)
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
