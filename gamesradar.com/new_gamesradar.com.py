from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.gamesradar.com/reviews', use='curl', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "subcategory-list")]/ul/li')
    for cat in cats:
        name = cat.xpath('h3//text()').string(multiple=True)
        url = cat.xpath('.//a/@href').string().replace('Reviews', '').strip()
        session.queue(Request(url, use='curl', max_age=0), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and int(current_page) == page:
        next_page = page + 1
        next_url = context['cat_url'] + 'page/{}'.format(next_page)
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('review:')[0].split('Review:')[0].replace(' review', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Games|' + context['cat']
    product.manufacturer = data.xpath('//strong[contains(., "Developer:")]/following-sibling::text()[1]').string()

    platforms = data.xpath('//strong[contains(., "Platform(s):")]/following-sibling::text()').string()
    if platforms:
        product.category += '|' + platforms.replace(', ', '/')

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
