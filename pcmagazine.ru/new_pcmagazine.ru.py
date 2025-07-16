from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://uk.pcmag.com/article/review', use='curl', force_charset='utf-8'), process_catlist, dict())
    session.queue(Request('https://uk.pcmag.com/security', use='curl', force_charset='utf-8'), process_subcatlist, dict(cat='Security'))


def process_catlist(data, context, session):
    cats = data.xpath('//a[contains(@class, "title")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_subcatlist, dict(cat=name))


def process_subcatlist(data, context, session):
    sub_cats = data.xpath('//a[@class="kwrelated"]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('text()').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=context['cat'] + '|' + sub_name))

    if not sub_cats:
        process_revlist(data, context, session)


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="swiper-slide"]/a[not(img)]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'These.+Memorial Day|the best|Our Best-Reviewed', title, flags=re.I) :
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Preview', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.url = data.xpath('//td[contains(@class, "buybutton")]/a/@href').string()
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

    author = data.xpath('//span[@class="reviewer hcard"]//text()').string()
    author_url = data.xpath('//span[@class="reviewer hcard"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="editor_rating"]/b/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split()[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//li[@class="pros-item"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[@class="cons-item"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@id="id_deck"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[b[regexp:test(., "verdict", "i")]]//text()[not(regexp:test(., "verdict", "i"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@id, "bottomline")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@id="id_text"]|//body)/p[not(@class or regexp:test(., "verdict", "i") or .//span[@class="Article_subtitle"])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
