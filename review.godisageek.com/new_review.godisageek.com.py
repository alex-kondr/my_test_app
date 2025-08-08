from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.godisageek.com/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    last_rev_url = data.xpath('//li[a[contains(text(), "Reviews")]]//li[@class="post-list"]/a/@href').string()
    session.queue(Request(last_rev_url, use='curl', force_charset='utf-8'), process_review, dict(url=last_rev_url))


def process_review(data, context, session):
    title = data.xpath('//h1//text()').string(multiple=True)

    product = Product()
    product.name = title.replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath('//div[span[contains(text(), "Developer")]]/span[@class="detail-content"]//text()').string(multiple=True)

    platforms = data.xpath('//div[span[contains(text(), "Platform")]]/span[@class="detail-content"]//text()').join('/')
    if platforms:
        product.category = 'Games|' + platforms

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()

    author = data.xpath('//a[span[@itemprop="author"]]/span/text()').string()
    author_url = data.xpath('//a[span[@itemprop="author"]]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="rating-value"]//text()[normalize-space(.)]').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="procon pro"]/p//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="procon con"]/p//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="bottomline"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="clearfix"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)

    next_url = data.xpath('//div[@class="previous-wrapper"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_review, dict(url=next_url))
