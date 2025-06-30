from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.realhomes.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="listing__link"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and int(current_page) == page:
        next_page = page + 1
        next_url = 'https://www.realhomes.com/reviews/page/{}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)

    product = Product()
    product.name = title.split(' review')[0].strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath('//div[@class="news-article"]/ol/li//text()[normalize-space(.)]').join('|') or 'Tech'

    product.url = data.xpath('//a[contains(@class, "merchantlink")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//time/@datetime').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('(//div|//span)[contains(@aria-label, "Rating: ")]/@aria-label').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].split('out of')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[@class="procon__pros"]/ul//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="procon__cons"]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "header")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(@id, "should-you-buy") or regexp:test(., "Should you buy|Is the Instant")]/following-sibling::p[preceding-sibling::h3[1][contains(@id, "should-you-buy") or regexp:test(., "Should you buy|Is the Instant")]]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="verdict__text"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(@id, "should-you-buy") or regexp:test(., "Should you buy|Is the Instant")]/preceding::p[not(@class or regexp:test(., "Weight:|Voltage:|Price:") or parent::div[@class="boxout__text"])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class or regexp:test(., "Weight:|Voltage:|Price:") or preceding::h3[regexp:test(., "Where to buy|How we tested|Good to know")] or parent::div[@class="boxout__text"] or preceding::div[contains(@class, "hero-product-container")])]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
