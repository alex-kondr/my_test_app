from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.macworld.com/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('O6 review:', '').replace('Lab tested: ', '').split(' Preview :')[0].split(' Preview:')[0].split(' Preview -')[0].split(' Preview –')[0].split(' Review:')[0].split(' Reviewed ')[0].replace('Preview ', '').replace('Review ', '').replace('Reviewed ', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('.html', '').replace('-review', '')

    product.url = data.xpath('//a[contains(., "View Deal")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//div[@class="single-breadcrumb"]//a[not(regexp:test(., "Home|Review"))]/text()').string()
    if category:
        product.category = category.strip(' /')
    else:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="posted-on"]/text()').string()
    if date:
        review.date = date.split(' am ')[0].split(' pm ')[0].strip().rsplit(' ', 1)[0].strip()

    author = data.xpath('//span[@class="author vcard"]//text()').string()
    author_url = data.xpath('//span[@class="author vcard"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="starRating"]/@style').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[-1].strip(' :;'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[h3[contains(., "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(., "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="subheadline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Should You Buy|Conclusion|Verdict", "i")]/following-sibling::p[not(regexp:test(., "^\$\d+|Check out the"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Our Verdict")]/following-sibling::p[not(regexp:test(., "Price When Reviewed|This value will show the geolocated|Best Pricing Today"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Should You Buy|Conclusion|Verdict", "i")]/preceding-sibling::p[not(regexp:test(., "^\$\d+"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(regexp:test(., "^\$\d+|Check out the"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(regexp:test(., "^\$\d+|Check out the"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
