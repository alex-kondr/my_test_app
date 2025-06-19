from agent import *
from models.products import *


XCAT = ['News']


def run(context, session):
    session.queue(Request('https://soundvisionreview.com/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-category-menu"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul[@class="sub-menu"]/li/a')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name+'|'+sub_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Sports Headphones Group Test:', '').replace('BoomBox Group Test:', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@href, "https://www.amazon.com/")]/@href').string()
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

    grade_overall = data.xpath('//span[contains(@class, "review-total")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace('%', '').strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//ul[@class="review-list"]/li/span')
    for grade in grades:
        grade_name = grade.xpath('.//text()').string(multiple=True).split('-')[0].strip()
        grade_val = grade.xpath('.//text()').string(multiple=True).split('-')[-1].strip(' %')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//div[strong[contains(., "PLUS")]]/text()[normalize-space(.)]')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[strong[contains(., "MINUS")]]/text()[normalize-space(.)]')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "text_element")]/p/span[@class="bold_text"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[h3[contains(., "Conclusion")]]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="review-desc"]/p[not(@class)]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "thrv_wrapper") and not(.//span[@class="bold_text"] or .//div[@class="review-desc"] or .//h3[@style])]//p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
