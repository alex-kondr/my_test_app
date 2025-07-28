from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.guitarplayer.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if int(current_page) != page:
        return

    revs = data.xpath('//div[@class="listingResults review"]/div')
    for rev in revs:
        title = rev.xpath('.//h3[@class="article-name"]/text()').string()
        url = rev.xpath('a[@class="article-link"]/@href').string()

        if title and url:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = 'https://www.guitarplayer.com/reviews/page/' + str(page+1)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=page+1))


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r' review$| reviewed$| Reviews$', '', context['title'].replace('We review the ', '').replace('Our reviewer says the ', '').replace('We reviewed the ', '').replace('Our reviewer hijacked an ', '').strip(), flags=re.I).strip()
    product.ssid = context['url'].split('/')[-1].replace('-reviewed', '').replace('-review', '')
    product.category = data.xpath('//div[@class="header-container" and nav[@class="breadcrumb"]]/ol/li[last()]/a/text()').string()

    product.url = data.xpath('//a[@data-merchant-url="https://www.thomann.de"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[@class="review-title-long"]//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(text(), "By")]/*/text()').string()
    author_url = data.xpath('//span[contains(text(), "By")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="chunk rating"]/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.replace('Rating:', '').split(' out of ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[@class="pretty-verdict__pros"]//li/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]//li/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h1[@class="review-title-long"]]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('((//p|//h2|//h3)[contains(., "Conclusion")])[last()]/following-sibling::p[not(regexp:test(., "SPECIFICATIONS", "i") or preceding::p[regexp:test(., "SPECIFICATIONS", "i")] or preceding::h2[regexp:test(., "SPECIFICATIONS", "i")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('((//p|//h2|//h3)[contains(., "Conclusion")])[last()]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(regexp:test(., "SPECIFICATIONS", "i") or preceding::p[regexp:test(., "SPECIFICATIONS", "i")] or preceding::h2[regexp:test(., "SPECIFICATIONS", "i")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
