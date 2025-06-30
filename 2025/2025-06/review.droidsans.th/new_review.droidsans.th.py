from agent import *
from models.products import *
import re


name_clearing = re.compile(r'Preview.?:|Review.?:|\[.+\]|Preview |Review |Blind Test.?:| Review', flags=re.I)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://droidsans.com/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'แนะนำมือถือ|รีวิวแท็บเล็ตโทรได้|มือถือราคาถูกที่สุด|แนะนำมือถือ .*รุ่น', title):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = name_clearing.sub('', context['title'].split('|')[-1]).split(' Test :')[-1].strip(' –')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    category = data.xpath('//a[@rel="tag" and not(contains(., "review"))]/text()').string()
    if category:
        product.category = category.replace(' Test', '').replace(' Review', '').strip()
    else:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="post-author"]/a//text()').string()
    author_url = data.xpath('//div[@class="post-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[contains(., "จุดเด่นของ")]/following-sibling::ul[1]/li/span')
    if not pros:
        pros = data.xpath('//p[contains(., "จุดเด่นของ")]/following-sibling::ol[1]/li/span')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "จุดพิจารณาของ")]/following-sibling::ul[1]/li/span')
    if not cons:
        cons = data.xpath('//p[contains(., "จุดพิจารณาของ")]/following-sibling::ol[1]/li/span')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "สรุปการใช้งาน|สรุปการใช้งาน|สรุปส่งท้าย")]/following-sibling::p[not(preceding::p[regexp:test(., "จุดเด่นของ|ราคาแ")] or regexp:test(., "จุดเด่นของ|ราคาแ|วางจำหน่ายในประเทศจีนที")) and preceding::h2[1][regexp:test(., "สรุปการใช้งาน|สรุปการใช้งาน|สรุปส่งท้าย")]]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "สรุปการใช้งาน|สรุปการใช้งาน|สรุปส่งท้าย")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "สรุปการใช้งาน|สรุปการใช้งาน|สรุปส่งท้าย")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="left-content"]/p[not(preceding::p[contains(., "จุดเด่นของ")] or contains(., "จุดเด่นของ") or preceding::h2[contains(., "ราคาแ")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
