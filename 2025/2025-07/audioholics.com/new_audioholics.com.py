from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.audioholics.com/product-reviews/archives/page/1', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//span[@class="description"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'Speaker Face-Off' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="page-link" and i[contains(@class, "right")]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'[\s]?[P]?review[ed]{0,2}[ -:]{0,3}| Overview| Bench.+Test Results', '', re.split(r' [p]?Review[ed]{0,2}[ :-]{1,3}', context['title'], flags=re.I)[0], flags=re.I).strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath('(//div[@class="row"]/ol/li/a)[last()]/text()').string().replace(' Reviews', '').strip()
    product.manufacturer = data.xpath('//li[contains(., "Manufacturer:")]//span/text()').string()

    product.url = data.xpath('//p[@class="mm-buy"]/a[contains(., "Buy Now")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="documentByLine" and contains(., "By")]/span[not(@class)]//text()').string(multiple=True)
    author_url = data.xpath('//div[@class="documentByLine" and contains(., "By")]/span[not(@class)]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//table[@class="metrics"]/tbody/tr')
    if not grades:
        grades = data.xpath('//li[contains(., "Rating:")]')

    for grade in grades:
        grade_name = grade.xpath('td[not(img)]//text()').string(multiple=True) or grade.xpath('text()').string(multiple=True)
        grade_name = grade_name.replace('Rating:', '').strip()
        grade_val = grade.xpath('count(.//img[@alt="Star"]) + count(.//img[@alt="half-star"]) div 2')
        if grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="ahReviewPros"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="ahReviewCons"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('(//p[contains(@class, "product-text")])[1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[regexp:test(., "Conclusion|Final Thoughts", "i")])[last()]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusion|Final Thoughts", "i")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "description")]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
