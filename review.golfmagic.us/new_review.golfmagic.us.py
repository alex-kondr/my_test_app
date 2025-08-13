from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.golfmagic.com/equipment/reviews', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "categories")]//div[@class="field-content"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="title" and (regexp:test(., "review", "i") or contains(@href, "review"))]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and url:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].split(' review: ')[0].replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(@class, "brand")]/div/a/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//address[@rel="author"]|//div[@class="col article-info"]//address)//text()').string(multiple=True)
    author_url = data.xpath('//address[@rel="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[contains(@class, "review-pros")]/div[@class="field-content"]//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "review-cons")]/div[@class="field-content"]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="summary body"]/p//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'�', '').strip()
        if len(summary) > 2:
            review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "verdict", "i")]/following-sibling::p[not(regexp:test(., "Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(., "verdict", "i")]/following-sibling::p[not(regexp:test(., "Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "Should you buy", "i")]/following-sibling::p[not(regexp:test(., "Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(., "Should you buy", "i")]/following-sibling::p[not(regexp:test(., "Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[regexp:test(., "verdict", "i")]]/following-sibling::p[not(regexp:test(., "Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'�', '').strip()
        if len(conclusion) > 2:
            review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "verdict", "i")]/preceding-sibling::p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(., "verdict", "i")]/preceding-sibling::p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "Should you buy", "i")]/preceding-sibling::p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(., "Should you buy", "i")]/preceding-sibling::p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[regexp:test(., "verdict", "i")]]/preceding-sibling::p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[@class="body" and p])[1]/p[not(regexp:test(., "Key Features|Buy it if:|Skip it if:|✅|❌|Watch our video review"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'�', '').strip()
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
