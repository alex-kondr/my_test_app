from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://inthegame.nl/category/nieuws/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h5[contains(@class, "post__title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review: ', '').replace('Review – ', '').replace('Review | ', '').replace('PC review: ', '').replace('Re-review: ', '').replace('Mini reviews: ', '').replace(' Review', '').replace('Retro review: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '').replace('-review', '')
    product.category = data.xpath('//span[@itemprop="name" and not(regexp:test(., "Home|Reviews|Nieuws|Previews"))]/text()').string() or 'Spellen'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[@class="typify-metadata"]/span[contains(@class, "author")]//text()').string(multiple=True)
    author_url = data.xpath('//p[@class="typify-metadata"]/span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="review-total-box"]/text()').string()
    if grade_overall:
        if '%' in grade_overall:
            grade_overall = float(grade_overall.replace('%', ''))
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))
        else:
            grade_overall = float(grade_overall.split('/')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    conclusion = data.xpath('(//h2|//p)[regexp:test(., "Verdict|Tot slot")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="review-desc"]/p[not(@class)]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//p)[regexp:test(., "Verdict|Tot slot")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "the_content")]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
