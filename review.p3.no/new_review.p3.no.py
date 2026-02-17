from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.nrk.no/filmpolitiet/'), process_revlist, dict(cat='Film'))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@data-id]')
    for rev in revs:
        ssid = rev.xpath('@data-id').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url, ssid=ssid))

    if context.get('next_url'):
        offset = context['offset'] + 6
        next_url = next_url.split('.offset=')[0] + str(offset) + '&' + next_url.split('.offset=')[-1].split('&', 1)[-1]
        session.queue(Request(next_url), process_revlist, dict(context, offset=offset))

    else:
        next_url = data.xpath('//button[contains(@class, "page-forward")]/@data-id[contains(., "size=18")]').string()
        if next_url:
            next_url = 'https://www.nrk.no/serum/api/render/' + next_url
            session.queue(Request(next_url), process_revlist, dict(next_url=next_url, offset=22))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//div[@class="review-info"]/h3/text()').string().strip('« »')
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    genres = data.xpath('//p[contains(text(), "Sjanger: ")]/text()').string()
    if genres:
        product.category += '|' + genres.replace('Sjanger: ', '').strip().replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="author__name"]/text()').string()
    author_url = data.xpath('//a[@class="author__name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('-')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="review-rating"]/span/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split()[-1]
        if grade_overall and float(grade_overall) > 0
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "article-lead")]/p/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
