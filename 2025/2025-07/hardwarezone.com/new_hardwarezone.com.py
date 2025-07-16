from agent import *
from models.products import *
import simplejson
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.hardwarezone.com.sg/_plat/api/teaser/latest?tags=editors-picks&ignoreIds=6805939%2C6973865%2C6972363%2C6959661%2C6806311%2C6805736%2C6805333%2C6805809%2C6805305%2C6805172%2C6805372%2C6805500%2C6823897&from=0&size=8&storyTypes=reviewStory', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = simplejson.loads(data.content).get('results', [])
    for rev in revs:
        ssid = str(rev.get('id'))
        title = rev.get('title')
        url = 'https://www.hardwarezone.com.sg' + rev.get('path')
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(ssid=ssid, title=title, url=url))

    if revs:
        offset = context.get('offset', 0) + 8
        next_url = 'https://www.hardwarezone.com.sg/_plat/api/teaser/latest?tags=editors-picks&ignoreIds=6805939%2C6973865%2C6972363%2C6959661%2C6806311%2C6805736%2C6805333%2C6805809%2C6805305%2C6805172%2C6805372%2C6805500%2C6823897&from={offset}&size=8&storyTypes=reviewStory'.format(offset=offset)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'[\s]?[P]?review[ed]{0,2}[ -:]{0,3}', '', re.split(r' [p]?Review[ed]{0,2}[ :-]{1,3}', context['title'], flags=re.I)[0], flags=re.I).strip()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = data.xpath('//div[h1[contains(@class, "title")]]/div[contains(@class, "label")]//div[contains(@class, "label")]/a/text()').join('|')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "authorLink")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "authorLink") and not(contains(@href, "/about-us"))]/@gref').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[h1[contains(@class, "title")]]/p/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3[regexp:test(., "Final thoughts|Conclusion")]|//p[regexp:test(., "Final thoughts|Conclusion")])/following-sibling::p[not(regexp:test(., "Image:|Our articles may contain| is available now on |Note: ") or contains(@class, "imageCaption"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[regexp:test(., "Final thoughts|Conclusion")]|//p[regexp:test(., "Final thoughts|Conclusion")])/preceding-sibling::p[not(regexp:test(., "Image:|Our articles may contain| is available now on |Note: ") or contains(@class, "imageCaption"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body")]/p[not(regexp:test(., "Image:|Our articles may contain| is available now on |Note: ") or contains(@class, "imageCaption"))]//text()').string(multiple=True)

    rev_id = data.xpath('//script[contains(., "__staticRouterHydrationData ")]/text()').string()
    if '%2Fcontent%2F' in rev_id:
        rev_id = rev_id.split('%2Fcontent%2F')[-1].split('%22', 1)[0]
        next_url = 'https://www.hardwarezone.com.sg/_plat/api/product/reviewById?id={}'.format(rev_id)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    rev_json = simplejson.loads(data.content).get('results', {})

    grades = rev_json.get('ratings', [])
    for grade in grades:
        grade_name = grade.get('key').title()
        grade_val = grade.get('value')
        if grade_name.lower() == 'overall':
            review.grades.append(Grade(type='overall', value=float(grade_val), best=10.0))
        else:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = rev_json.get('pros', [])
    for pro in pros:
        pro = pro.get('value')
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = rev_json.get('cons', [])
    for con in cons:
        con = con.get('value')
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if context['excerpt']:
        context['excerpt'] = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
