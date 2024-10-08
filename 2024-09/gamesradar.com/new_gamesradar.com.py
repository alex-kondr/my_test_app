from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gamesradar.com/reviews/archive/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[@class=""]//a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[@class="day-article"]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('review:')[0].split('Review:')[0].replace(' review', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    platforms = data.xpath('//strong[contains(., "Platform(s):")]/following-sibling::text()').string()
    cats = data.xpath('//ol/li/span/span/a[@data-before-rewrite-localise]/text()').strings()
    if not cats:
        cats = data.xpath('//ol/li/span/a[@data-before-rewrite-localise]/text()').strings()

    if cats and platforms:
        product.category = '|'.join([cat.strip() for cat in cats]) + '|' + platforms.replace(', ', '/')
    elif cats:
        product.category = '|'.join([cat.strip() for cat in cats])

    product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
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

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "verdict")]//span/@aria-label').string()
    if not grade_overall:
        grade_overall = data.xpath('//span[@class="chunk rating"]/@aria-label').string()

    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('out')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[@class="pretty-verdict__pros"]/ul//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.lstrip(' +-')
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.lstrip(' +-')
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2//text()').string(multiple=True)
    if summary and len(summary) > 2:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")]|//h2[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")])/following-sibling::p[not(preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Verdict")]]/following-sibling::p[not(contains(., "@") or preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Verdict:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

        if not summary:
            summary = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)
            if summary and len(summary) > 2:
                review.add_property(type='summary', value=summary)


    if not conclusion:
        conclusion = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)
        if conclusion:
            conclusion = conclusion.replace('Verdict:', '').strip()
            review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")]|//h2[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")])/preceding-sibling::p[not(preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[contains(., "Verdict")]]/preceding-sibling::p[not(preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(regexp:test(., "^For more") or preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
