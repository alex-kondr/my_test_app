from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://brutalgamer.com/'), process_frontpage, {})
    session.queue(Request('https://brutalgamer.com/category/reviews/hardware-reviews/'), process_revlist, dict(cat='Hardware'))
    session.queue(Request('https://brutalgamer.com/category/reviews/'), process_revlist, {})    # For the rest of reviews which don't have a category



def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "menu-item-object-category") and contains(., "Reviews")]/div/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string().replace(' Reviews', '')
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post-listing")]/h2[@class="post-box-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review')[0].split(' Review')[0].split(' REVIEW')[0].replace('Review: ', '').replace(' (Anime Recap/Review)', '').replace(' (Review)', '').replace(' – Video Game Preview', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//body[@id="top"]/@class').string().split('id-')[-1].split()[0]
    product.category = context.get('cat') or 'Games'
    product.manufacturer = data.xpath('//p/text()[preceding-sibling::*[1][self::strong[regexp:test(., "Publisher:|Published by:|Written by:|Maker:|Developer:|Produced by:|Manufacturer:")]]]').string()

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="post-meta-author"]/a//text()').string()
    author_url = data.xpath('//span[@class="post-meta-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]/h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('h5/span/text()').string()
        grade_value = grade.xpath('.//span/@data-width').string()
        if grade_name and grade_value:
            grade_name = grade_name.split(' - ')[0].strip()
            review.grades.append(Grade(name=grade_name, value=float(grade_value), best=100.0))

    conclusion = data.xpath('//div[@class="entry"]/p[preceding-sibling::*[self::h1 or self::h2 or self::h3 or self::h4 or self::p[strong]][regexp:test(., "final thought|conclusion|overall|Final Say", "i")]][not(regexp:test(., "copy of|for this review"))][not(.//strong[contains(., "Platform:|Developer:|MSRP|Produced by:|Written by:|Published by:|Release Date:")])]//text()[not(regexp:test(., "copy provided by", "i"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="entry"]/p[strong[regexp:test(., "final thought|conclusion|overall|Final Say", "i")]][not(regexp:test(., "copy of|for this review"))][not(.//strong[contains(., "Platform:|Developer:|MSRP|Produced by:|Written by:|Published by:|Release Date:")])]/text()[not(regexp:test(., "copy provided by", "i"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//h2[@class="review-box-header"]/text()').string()
    if summary and not conclusion:
        review.add_property(type='summary', value=summary)
    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//div[@class="entry"]/p[not(preceding::*[regexp:test(., "final thought|conclusion|overall|Final Say", "i")])][not(*[regexp:test(., "final thought|conclusion|overall|Final Say", "i")])][not(.//strong[regexp:test(., "Platform:|Developer:|MSRP|Produced by:|Written by:|Published by:|Release Date:")])]//text()[not(regexp:test(., "copy provided by", "i"))]').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
