from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://gizmodo.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "items-center")]/a[span]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[h3[contains(@class, "link-main")]]/a')
    for rev in revs:
        url = rev.xpath('@href').string()

        if '-vs-' not in url:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//h1//text()').string(multiple=True)
    if not title:
        return

    product = Product()
    product.name = re.sub(r' Review$| Reviewed$', '', title.replace('Gizmodo Reviews:', '').split(' Review: ')[0]).replace(' review', '').replace(' Review', '').replace('I Tested ', '').replace('We Tested ', '').strip()
    product.ssid = context['url'].split('-')[-1]
    product.category = context['cat'].replace('Other', '').strip()

    product.url = data.xpath('//a[@rel="sponsored nofollow"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author_url = data.xpath('//span[contains(text(), "By")]/a[@rel="author"]/@href').string()
    author = data.xpath('//span[contains(text(), "By")]/a[@rel="author"]/text()').string()
    if not author:
        author = data.xpath('//div[time]/div/text()').string()

    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//i[@class="fas fa-star"]) + count(//i[contains(@class, "fa-star-half")]) div 2')
    if not grade_overall:
        grade_overall = data.xpath('//div[i[contains(@class, "fa-star")]]/span/text()').string()

    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[p[contains(., "Pros")]]/ul/li')
    if not pros:
        pros = data.xpath('//p[contains(., "LIKE")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "NO LIKE")] or regexp:test(., "NO LIKE"))]')
    if not pros:
        pros = data.xpath('//div[div/p[contains(text(), "Pros")]]/ul/li')
    if not pros:
        pros = data.xpath('''//p[contains(., "Like")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Don't Like")] or regexp:test(., "Don't Like"))]''')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[p[contains(., "Cons")]]/ul/li')
    if not cons:
        cons = data.xpath('//p[contains(., "NO LIKE")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Should .+ Buy .+?", "i")] or regexp:test(., "Should .+ Buy .+?", "i"))]')
    if not cons:
            cons = data.xpath('//div[div/p[contains(text(), "Cons")]]/ul/li')
    if not cons:
        cons = data.xpath('''//p[contains(., "Don't Like")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Should .+ Buy .+?", "i")] or regexp:test(., "Should .+ Buy .+?", "i"))]''')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[regexp:test(., "Should .+ Buy .+?|README", "i")]/following-sibling::p[not(preceding-sibling::h4 or preceding-sibling::h3[regexp:test(., "Spec", "i")] or regexp:test(., "https:|Spec", "i"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review")]//p[contains(@class, "text-lg")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-box")]/div/div/p[contains(@class, "text-xl")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('''//h3[regexp:test(., "Should .+ Buy .+?", "i")]/preceding-sibling::p[not(preceding-sibling::p[regexp:test(., "LIKE|NO LIKE")] or regexp:test(., "LIKE|NO LIKE|Don't Like", "i"))][not(@class)]//text()''').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@class or preceding::h3[regexp:test(., "README|SPEC")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
