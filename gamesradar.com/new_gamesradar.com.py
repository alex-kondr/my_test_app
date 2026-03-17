from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


XCAT = ['Open World']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.gamesradar.com/reviews'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "subcategory-list")]/ul/li')
    for cat in cats:
        genre = cat.xpath('h3//text()').string(multiple=True).replace('Reviews', '').strip()
        url = cat.xpath('.//a/@href').string()

        if genre not in XCAT:
            session.queue(Request(url), process_revlist, dict(genre=genre, cat_url=url))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "item-link")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and int(current_page) == page:
        next_page = page + 1
        next_url = context['cat_url'] + 'page/{}'.format(next_page)
        session.queue(Request(next_url), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    if not title:
        title = data.xpath('//div[contains(@class, "article")]/h1/text()').string()

    product = Product()
    product.name = title.split('review:')[0].split('Review:')[0].replace(' review', '').replace(' Review', '').replace(' | Preview', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.manufacturer = data.xpath('//strong[contains(., "Developer:")]/following-sibling::text()[1]').string()

    product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('//strong[regexp:test(., "Platform")]/following-sibling::text()').string()
    if platforms and context['genre'] not in platforms:
        product.category = 'Games|' + platforms.strip(' :').replace(', ', '/') + '|' + context['genre']
    elif platforms:
        product.category = 'Games|' + platforms.replace(', ', '/')
    elif context['genre'] not in ['Tech', 'TV Shows', 'Games']:
        product.category = 'Games|' + context['genre']
    else:
        product.category = context['genre']

    product.category = product.category.replace(' (with Xbox Series X still to come/though currently', '').replace(' (Nintendo Switch TBC)', '').replace(' (Announced)', '').replace(' (at a later date)', '').replace('X/S', 'X\\S')

    review = Review()
    review.type = 'pro'
    review.title = title
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
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2//text()').string(multiple=True)
    if summary and len(summary) > 2:
        summary = h.unescape(summary).replace('%26ndash;', '-').replace('%26rsquo;', "'").replace('%26ldquo;', '"').replace('%26rdquo;', '"').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")]|//h2[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")])/following-sibling::p[not(preceding-sibling::h2[contains(., "How we tested") or contains(., "How I tested")] or preceding::p[@class="infoDisclaimer"])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Verdict")]]/following-sibling::p[not(contains(., "@") or preceding-sibling::h2[contains(., "How we tested") or contains(., "How I tested")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).replace('%26ndash;', '-').replace('%26rsquo;', "'").replace('%26ldquo;', '"').replace('%26rdquo;', '"').replace('Verdict:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

        if not summary:
            summary = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)
            if summary and len(summary) > 2:
                summary = h.unescape(summary).replace('%26ndash;', '-').replace('%26rsquo;', "'").replace('%26ldquo;', '"').replace('%26rdquo;', '"').strip()
                review.add_property(type='summary', value=summary)

    if not conclusion:
        conclusion = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)
        if conclusion:
            conclusion = h.unescape(conclusion).replace('Verdict:', '').replace('%26ndash;', '-').replace('%26rsquo;', "'").replace('%26ldquo;', '"').replace('%26rdquo;', '"').strip()
            review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")]|//h2[contains(., "Overall") or contains(., "should you buy") or contains(., "Should you buy")])/preceding-sibling::p[not(preceding-sibling::h2[contains(., "How we tested")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[contains(., "Verdict")]]/preceding-sibling::p[not(preceding-sibling::h2[contains(., "How we tested") or contains(., "How I tested")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(regexp:test(., "^For more") or preceding-sibling::h2[contains(., "How we tested") or contains(., "How I tested")] or preceding::p[@class="infoDisclaimer"])]//text()').string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).replace('%26ndash;', '-').replace('%26rsquo;', "'").replace('%26ldquo;', '"').replace('%26rdquo;', '"').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
