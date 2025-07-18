from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.pcworld.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(., "Reviews")]]/ul//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string().replace('&amp', '&')
        url = rev.xpath('@href').string().rsplit('/', 1)[0]
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'Tested: |Test: |Reviewed: | review|: How We Test|Review: | Review| Tests|Book Review – | review: ', '', re.split(r' preview: | review: | tested: | in test: | speed test: | re-review: ', context['title'], flags=re.I)[0]).strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']

    product.url = data.xpath('//a[contains(., "View Deal")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="posted-on"]/text()').string()
    if date:
        review.date = date.split(' am ')[0].rsplit(' ', 1)[0]

    author = data.xpath('//span[@class="author vcard"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="author vcard"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="starRating"]/@style').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[-1].strip(' ;'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[h3[contains(text(), "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(text(), "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="subheadline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(@id, "should-.+-buy") or regexp:test(text(), "Should .+ buy|It has a fan|conclusion|Final thoughts", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[@id="our-verdict"]/following-sibling::p[not(regexp:test(., "Price When Reviewed|This value will show the geolocated pricing text for product undefined|Best Pricing Today"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(@id, "should-.+-buy") or regexp:test(text(), "Should .+ buy|It has a fan|conclusion|Final thoughts", "i")]/preceding-sibling::p[string-length(.)>10]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//body/p[string-length(.)>10]|//div[contains(@class, "content")])[not(preceding-sibling::h3[1][@class="review-price"])]//text()[not(parent::span[contains(@class, "price")])][string-length(normalize-space(.))>10]').string(multiple=True)

    if excerpt:
        if not conclusion and 'Overall, ' in excerpt:
            excerpt, conclusion = excerpt.rsplit('Overall, ', 1)

            conclusion = conclusion.strip().title()
            review.add_property(type='conclusion', value=conclusion)

        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = excerpt.strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
