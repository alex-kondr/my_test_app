from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.runnersworld.com/uk/gear/shoes/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Shoes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/clothes/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Clothes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/tech/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Tech'))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@data-theme-key="custom-item"]')
    for rev in revs:
        title = rev.xpath('.//h3/span[contains(@class, "title-text")]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    data_json = data.xpath('''//script[contains(., '"contentId":"')]/text()''').string()
    if data_json:
        cat_id = simplejson.loads(data_json).get('metadata', {}).get('contentId')
        next_url = 'https://www.runnersworld.com/uk/api/feed-content/?id={}&type=subsection&limit=12&token=2&offset=13&params=%7B%22isHomePage%22%3Afalse%2C%22contentSectionEnabled%22%3Atrue%7D'.format(cat_id)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist_next, dict(context, cat_id=cat_id))


def process_revlist_next(data, context, session):
    revs = simplejson.loads(data.content).get('data', {}).get('feedInfo', [{}])[0].get('feedContent')
    for rev in revs:
        ssid = rev.get('display_id')
        title = rev.get('metadata', {}).get('short_title')


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//').string()
    author_url = data.xpath('//').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('//')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
