from agent import *
from models.products import *
import httplib


httplib._MAXHEADERS = 1000


def run(context, session):
    options = "--compressed -X POST --data-raw 'action=loadmore&page=0&category=723'"
    session.do(Request('https://www.sammobile.com/wp-admin/admin-ajax.php', use='curl', options=options, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="article-item article-item-flex"]/a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    if revs:
        page = context.get('page', 0) + 1
        options = "--compressed -X POST --data-raw 'action=loadmore&page={page}&category=723'".format(page=page)
        session.do(Request('https://www.sammobile.com/wp-admin/admin-ajax.php', use='curl', options=options, max_age=0), process_revlist, dict(page=page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('review:')[0].split('hands-on:')[0].split('review roundup:')[0].replace('Review:', '').strip(' review')
    product.url = context['url']
    product.ssid = product.name.lower().replace(' ', '-')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Overall score")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split()[-1]
        review.grades.append(Grade(type='overall', value=float(grade_overall)))

    pros = data.xpath('//span[i[@class="fas fa-check"]]')
    if not pros:
        pros = data.xpath('//p[regexp:test(., "^Con\'s$")]/preceding-sibling::p[contains(., "•")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip('•+- ')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[i[@class="fas fa-times"]]')
    if not cons:
        cons = data.xpath('//p[regexp:test(., "^Con\'s$")]/following-sibling::p[contains(., "•")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip('•+- ')
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h3[contains(., "Verdict")]|//p[contains(., "Conclusion")])/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//strong[contains(., "Conclusion")]/following-sibling::text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Conclusion")]]/following-sibling::p//text()')
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[contains(., "Conclusion")]]/preceding-sibling::p[not(contains(., "Conclusion"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Overall score")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "^Pro\'s$")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)