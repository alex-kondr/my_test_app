from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://the-gadgeteer.com/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(@class, "next")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'[\s]?[P]?review[ed]{0,2}[ -–:]{0,3}', '', re.split(r' [p]?Review[ed]{0,2}[ :-–]{1,3}', context['title'], flags=re.I)[0], flags=re.I).strip()
    product.ssid = context['url'].split('/')[-2].replace('_review', '').replace('-review', '')

    category = data.xpath('//span[@class="ast-terms-link"]/a[contains(@href, "https://the-gadgeteer.com/tag/") and not(regexp:test(., "review|home|contest", "i"))]/text()').string()
    if category:
        product.category = category.title()
    else:
        product.category = 'Tech'

    product.url = data.xpath('//strong[contains(., "Where to buy")]/following-sibling::a[not(contains(@href, "https://www.edifier.com/us/"))]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime|//span[@class="published"]/text()').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h2[contains(., "What I like")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('//h2[contains(., "What I like")]/following-sibling::p[(preceding-sibling::h2)[last()][contains(., "What I like")] and not(@class)]')
    if not pros:
        pros = data.xpath('//tr[td[contains(., "Pros")]]/td[@class="value"]//li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h2[contains(., "What needs")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('//h2[contains(., "What needs")]/following-sibling::p[(preceding-sibling::h2)[last()][contains(., "What needs")] and not(@class)]')
    if not cons:
        cons = data.xpath('//tr[td[contains(., "Cons")]]/td[@class="value"]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[.//strong[contains(., "REVIEW")]]//text()').string(multiple=True)
    if summary:
        summary = summary.replace('REVIEW', '').replace(u'\uFEFF', '').strip(' –:')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3)[regexp:test(., "Final thoughts|Conclusion")]/following-sibling::p[not(@class or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[regexp:test(., "Final thoughts|Conclusion")]/following-sibling::p[not(@class or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//h3)[regexp:test(., "Final thoughts|Conclusion")]/preceding-sibling::p[not(@class or .//strong[contains(., "REVIEW")] or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h2|//h3)[regexp:test(., "Final thoughts|Conclusion")]/preceding-sibling::p[not(.//strong[contains(., "REVIEW")] or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "Final thoughts|Conclusion")]/preceding-sibling::p[not(@class or .//strong[contains(., "REVIEW")] or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(@class or .//strong[contains(., "REVIEW")] or regexp:test(., ".+:.+\+|Where to buy|•") or (preceding-sibling::h2)[last()][contains(., "specs")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if 'In summary' in excerpt and not conclusion:
            excerpt, conclusion = excerpt.split('In summary')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
