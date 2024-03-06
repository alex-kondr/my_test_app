from agent import *
from models.products import *
import simplejson


XCAT = ['Buyer’s Guide', 'Privacy Policy', 'Guide']


def run(context, session):
    session.queue(Request('https://www.reviewguidelines.com/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="menu"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul[@class="sub-menu menu-sub-content"]/li')

            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('a/text()').string()

                    sub_cats1 = sub_cat.xpath('ul[@class="sub-menu menu-sub-content"]/li/a')
                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('text()').string()
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url, use='curl'), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url, use='curl'), process_revlist, dict(cat=name + '|' + sub_name))

            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//li[@class="the-next-page"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(': Review', '').replace(' – Review', '').replace('Review', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.url = data.xpath('//div[@class="one_third tie-columns last"]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style').string()
    if grade_overall:
        grade_overall = grade_overall.replace('width:', '').replace('%', '')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('h5/text()').string()
        grade_value = grade.xpath('.//span/@style').string().replace('width:', '').replace('%', '')
        review.grades.append(Grade(name=grade_name, value=float(grade_value), best=100.0))

    pros = data.xpath('//strong[contains(., "PROS")][normalize-space(following-sibling::text())]')
    for pro in pros:
        pro = pro.xpath('following-sibling::text()').string().replace('N/A.', '').replace('N/A', '').replace('n/a', '').replace('-', '').strip()
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//strong[contains(., "CONS")][normalize-space(following-sibling::text())]')
    for con in cons:
        con = con.xpath('following-sibling::text()').string().replace('N/A.', '').replace('N/A', '').replace('n/a', '').replace('-', '').strip()
        if con:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="entry-content entry clearfix"]//h2[1]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content entry clearfix"]//p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
