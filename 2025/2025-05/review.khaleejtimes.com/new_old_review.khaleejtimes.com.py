from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.khaleejtimes.com/contentapi/v1/getcollectionstories/tech-reviews-reviews?page=1&records=10', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content).get('data', {})

    revs = revs_json.get('child_stories', [])
    for rev in revs:
        title = rev.get('headline')
        ssid = rev.get('id')
        url = rev.get('url')
        if title and url:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, ssid=ssid, url=url))

    revs_cnt = revs_json.get('total_child_stories_count')
    offset = context.get('offset', 0) + 10
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.khaleejtimes.com/contentapi/v1/getcollectionstories/tech-reviews-reviews?page={}&records=10'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=next_page, offset=offset))


def process_review(data, context, session):
    if 'Best of' in context['title']:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].replace('Gadget Review:', '').replace('Tech Review:', '').replace('Partner Content:', '').split(' Review:')[0].split(' review: ')[0].replace('Review: ', '').replace('REVIEW:', '').replace('Review ', '').strip()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p[contains(., "Published:")]//text()').string()
    if date:
        review.date = date.split(' ', 2)[-1].split(',')[0].strip()

    author = data.xpath('//div[contains(@class, "auther")]//li//a[@class=""]/text()').string()
    author_url = data.xpath('//div[contains(@class, "auther")]//li//a[@class=""]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "stars")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split()[0].strip(u' \u202c\u202d')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//p[contains(., "Hits")]/following-sibling::p[not(preceding-sibling::p[contains(., "Misses")] or contains(., "Misses"))][normalize-space(.)]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(u'-+.•‭‬ ')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Misses")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Verdict|ALSO READ|Price")] or regexp:test(., "Verdict|ALSO READ|Price"))][normalize-space(.)]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(u'-+.•‭‬ ')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="recent"]//p[contains(@class, "preamble")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[.//strong[contains(., "Verdict")]]/following-sibling::p[not(preceding-sibling::p[contains(., "ALSO READ")] or contains(., "ALSO READ"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Verdict")]/following-sibling::p[not(preceding-sibling::p[contains(., "ALSO READ")] or contains(., "ALSO READ"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "Hits")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Misses")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[regexp:test(@class, "inner|recent")]/p[not(@class or contains(., "For more information") or .//strong[regexp:test(., "\w+:|Specifications")] or preceding::h3[contains(., "Verdict")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//h2[.//strong]')
    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('.//text()').string(multiple=True)
        product.ssid = product.name.lower().replace(' ', '-')
        product.url = context['url']
        product.category = 'Tech'

        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.url = product.url
        review.ssid = product.ssid

        date = data.xpath('//p[contains(., "Published:")]//text()').string()
        if date:
            review.date = date.split(' ', 2)[-1].split(',')[0].strip()

        author = data.xpath('//div[contains(@class, "auther")]//li//a[@class=""]/text()').string()
        author_url = data.xpath('//div[contains(@class, "auther")]//li//a[@class=""]/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        summary = data.xpath('//div[@class="recent"]//p[contains(@class, "preamble")]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h2[.//strong])={} and not(.//strong)]//text()'.format(i)).string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)

