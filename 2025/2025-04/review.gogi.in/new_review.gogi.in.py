from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.gogi.in/review", use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "list-blog") or @class="bs-blog-post"]')
    for rev in revs:
        title = rev.xpath('h4/a/text()').string()
        url = rev.xpath('h4/a/@href').string()
        author_name = rev.xpath('.//span[@class="bs-author"]/a/text()').string()
        author_url = rev.xpath('.//span[@class="bs-author"]/a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url, author_name=author_name, author_url=author_url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Unboxing and Overview of the', '').replace('Unboxing and In-Depth Review of the', '').replace('Unboxing and Review of the', '').replace('Unboxing and First Impressions:', '').replace('Unboxing the', '').split('review')[0].split('Review')[0].split('unboxing')[0].split('(')[0].split(' – ')[0].split(', ')[0].replace('Unboxing ', '').strip()
    product.ssid = context['url'].split('/')[-1].replace(".html", '').replace('-review', '')
    product.category = data.xpath('//div[@class="bs-blog-category"]/a[not(contains(., "Review"))]/text()').string() or 'Tech'

    product.url = data.xpath('//a[regexp:test(., "buy", "i") or contains(., "Via ") or regexp:test(., "available on ", "i")]/@href').string()
    if not product.url:
        product.url = data.xpath('//p[regexp:test(., "buy", "i") or contains(., "Via ") or regexp:test(., "available on ", "i")]/a/@href').string() or context['url']

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author_name = context.get('author_name')
    author_url = context.get('author_url')  # url with all revs by author
    if author_name and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid))
    elif author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = None
    rating = data.xpath('//div[@class="bs-blog-post"]/*[(regexp:test(., "rating", "i")) and (contains(., "out of") or contains(., "/"))]')
    for rate in rating[::-1]:
        rate = rate.xpath('.//text()').string(multiple=True)
        grade_overall = rate.lower().replace(' ', '').replace(':', '').split('outof')[0].split('/')[0].split('rating')[-1].replace('is', '').replace('-', '').replace('/', '')
        if "=" in grade_overall:
            grade_overall = grade_overall.split("=")[-1]
        try:
            grade_overall = float(grade_overall)
            break
        except:
            grade_overall = None
            continue

    if not grade_overall:
        grade_overall = len(data.xpath("//span[contains(., '★')]"))
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    conclusion = data.xpath('//div[@class="bs-blog-post"]/*[self::h2 or self::p or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion:", "i") or contains(., "Conclusion")]//text() | //div[@class="bs-blog-post"]/*[self::h2 or self::p or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion:", "i") or contains(., "Conclusion")]/following-sibling::p[not(contains(., "[poll") or regexp:test(., "buy here|Pros:|Cons:|Recommended For:|verdict", "i") or regexp:test(., "you can buy", "i") or regexp:test(., "available on", "i")) and not(a[contains(@href, "amzn.to")])][not(preceding-sibling::*[self::h2 or self::h3][1][regexp:test(., "rating", "i")])][not(preceding::*[regexp:test(., "buy here", "i")][1])]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Final Verdict:', '').replace('Verdict', '').replace('In conclusion,', '').replace('Conclusion', '').strip(' :')
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//p[not(preceding::span[contains(@id, "more")])]//text()').string()
    excerpt = data.xpath('//div[@class="bs-blog-post"]//p[not(regexp:test(., "you can buy|Verdict|• ", "i") or regexp:test(., "buy here", "i") or regexp:test(., "available on", "i") or regexp:test(., "watch video", "i") or contains(., "Conclusion")) and not(a[contains(@href, "amzn.to")])][not(preceding-sibling::*[self::h2 or self::p or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion:", "i") or contains(., "Conclusion")])][not(regexp:test(., "conclusion:", "i"))][not(*[(regexp:test(., "rating", "i")) and (contains(., "out of") or contains(., "/"))])]//text()').string(multiple=True)
    if excerpt and summary and len(excerpt.replace(summary, '').strip()) > 3:
        review.add_property(type='summary', value=summary.strip())
    elif summary:
        excerpt = summary

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        if summary:
            excerpt = excerpt.replace(summary, '')

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
