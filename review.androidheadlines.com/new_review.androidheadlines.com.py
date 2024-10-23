from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.androidheadlines.com/category/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "post-holder")]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    if re.search("Top \d+", context['title']):
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].replace('Featured Review:', '').replace(' Hands-On Preview', '').replace('Video:', '').split(' Review: ')[0].split(' Review – ')[0].split(' Review — ')[0].split(' Review-')[0].split(' review: ')[0].split(' review – ')[0].replace(' In Review', '').replace('Review: ', '').replace(' Review!', '').replace(' Review', '').split(' – ')[0].strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = 'Tech'

    product.category = data.xpath('//a[@class="taxonomy category" and not(regexp:test(., "News|Reviews"))]//text()').string()
    if not product.category:
        product.category = 'Tech'

    product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content[contains(., "T")]').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="entry-meta-author-name"]//a/text()').string()
    author_url = data.xpath('//div[@class="entry-meta-author-name"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//span[contains(., "Share this page") and @property]/preceding::head/title[text()="star"])')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[@class="col-md-6" and normalize-space(.//span[@class="h3"]/text())="Pros"]/ul/li')
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "Good")]]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//h2[contains(., "The Good")]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="col-md-6" and normalize-space(.//span[@class="h3"]/text())="Cons"]/ul/li')
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "Bad")]]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//h2[contains(., "The Bad")]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="lead"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "should you buy", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "right for you?", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "worth the money?", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "conclusion", "i")]/following-sibling::p//text()').string(multiple=True)
    if  not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "final", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="row"]//div[@class="col-12"]/p[not(@class)]//span[@property="itemListElement" and not(.//label or .//input or contains(., "Sign up to receive the latest"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "should you buy", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "right for you?", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "worth the money?", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "conclusion", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "final", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    prods = data.xpath("//h1[@id='title']")
    if not prods:
        prods = data.xpath('//p[@id="title"] | //p[.//strong][not(contains(., "Sign up") or contains(., "Deals & More") or contains(., "Main") or contains(., "Android News"))]')
    if not prods:
        prods = data.xpath('//*[self::h1 or self::h2][@id="title"]')

    for i, prod in enumerate(prods, start=1):
        name = prod.xpath(".//text()").string(multiple=True)
        if not name or "Top" in name:  # if don't page title
            continue

        product = Product()
        product.name = name
        product.url = context["url"]
        product.ssid = product.name.lower().replace(' ', '_').replace('-', '').replace('—', '').replace('__', '_')

        product.category = data.xpath('//a[@class="taxonomy category" and not(regexp:test(., "News|Reviews"))]//text()').string()
        if not product.category:
            product.category = 'Tech'

        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = product.url
        review.ssid = product.ssid

        date = data.xpath('//meta[@property="article:published_time"]/@content[contains(., "T")]').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//div[@class="entry-meta-author-name"]//a/text()').string()
        author_url = data.xpath('//div[@class="entry-meta-author-name"]//a/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = prod.xpath('following-sibling::p[count(preceding-sibling::h1[@id="title"])={i} and not(.//img)]//text()'.format(i=i)).string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
