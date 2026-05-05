from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.pcworld.com/reviews'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[contains(@class, "tab-item")]/a[contains(., " Reviews")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string().replace('&amp', '&')
        url = rev.xpath('@href').string().rsplit('/', 1)[0]

        if ' vs. ' not in title:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' preview: ')[0].split(' Preview: ')[0].split(' review: ')[0].split(' Review: ')[0].split(' tested: ')[0].split(' Tested: ')[0].split(' in test: ')[0].split(' In test: ')[0].split(' speed test: ')[0].split(' Speed test: ')[0].split(' re-review: ')[0].split(' Re-review: ')[0].split(' review: ')[0].split(': Testing ')[0].split(': We test ')[0].replace('Tested: ', '').replace('Test: ', '').replace('Reviewed: ', '').replace(': How We Test', '').replace('Review: ', '').replace(' Tests', '').replace('Book Review – ', '').replace(' review: ', '').replace(' review', '').replace(' Review', '').replace('Review impressions: ', '').replace('Tested! ', '').replace('Tests ', '').strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat'].replace(' Reviews', '').strip()

    product.url = data.xpath('//a[contains(., "View Deal")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@class, "price")]/@href').string()
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
    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(., "Final Rating:")]/text()').string()

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
        summary = summary.replace(u'\x7F', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(@id, "should-.+-buy") or regexp:test(text(), "Should .+ buy|It has a fan|conclusion|Final thoughts", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[@id="our-verdict"]/following-sibling::p[not(regexp:test(., "Price When Reviewed|This value will show the geolocated pricing text for product undefined|Best Pricing Today"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\x7F', '').replace('Overall, ', '').strip()
        conclusion = conclusion[0].title() + conclusion[1:]
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(@id, "should-.+-buy") or regexp:test(text(), "Should .+ buy|It has a fan|conclusion|Final thoughts", "i")]/preceding-sibling::p[string-length(.)>10]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//body/p[string-length(.)>10]|//div[contains(@class, "content")])[not(preceding-sibling::h3[1][@class="review-price"])]//text()[not(parent::span[contains(@class, "price")] or regexp:test(., "Rating:|Price:"))][string-length(normalize-space(.))>10]').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\x7F', '').strip()

        if not conclusion and 'Overall, ' in excerpt:
            excerpt, conclusion = excerpt.rsplit('Overall, ', 1)

            conclusion = conclusion.strip()[0].title() + conclusion.strip()[1:]
            review.add_property(type='conclusion', value=conclusion)

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        excerpt = excerpt.strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
