from agent import *
from models.products import *
import simplejson
from datetime import datetime


XTITLE = ['Best of']


def run(context, session):
    session.queue(Request('https://www.khaleejtimes.com/contentapi/v1/getcollectionstories/tech-reviews-reviews?page=1&records=10', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content).get('data', {})

    revs = revs_json.get('child_stories', [])
    for rev in revs:
        title = rev.get('headline')
        ssid = rev.get('id')
        url = rev.get('url').split('?')[0]

        if title and url and not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, ssid=ssid, url=url))

    revs_cnt = revs_json.get('total_child_stories_count', 0)
    offset = context.get('offset', 0) + 10
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.khaleejtimes.com/contentapi/v1/getcollectionstories/tech-reviews-reviews?page={}&records=10'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=next_page, offset=offset))


def process_review(data, context, session):
    rev_json = data.xpath('//div/@data-page').string()
    try:
        rev_json = simplejson.loads(rev_json).get('props', {}).get('story_data')
    except:
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

    date = rev_json.get('created_at')
    if date:
        review.date = datetime.fromtimestamp(date / 1000).strftime("%d.%m.%Y")

    authors = rev_json.get('authors', [])
    for author in authors:
        author_ssid = author.get('id')
        author_name = author.get('name')
        author_url = 'https://www.khaleejtimes.com/author/' + author.get('slug')
        if author_name:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid), profile_url=author_url))

    excerpts_json = rev_json.get('cards', [{}])[0].get('story_elements', [])
    new_data = '<div>'
    for excerpt_json in excerpts_json:
        if excerpt_json.get('type') == 'text':
            new_data += excerpt_json.get('text')

    new_data += '</div>'
    new_data = data.parse_fragment(new_data)

    grade_overall = new_data.xpath('//p[contains(strong, "Rating")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].strip()
        if grade_overall:
            grade_overall = grade_overall.split()[0].replace(u'\u202d', '').replace(u'\u202c', '').strip()
        else:
            grade_overall = new_data.xpath('//p[contains(strong, "Rating")]/following-sibling::p[1][contains(., "stars")]//text()').string(multiple=True)
            if grade_overall:
                grade_overall = grade_overall.split()[0].replace(u'\u202d', '').replace(u'\u202c', '').strip()

        if grade_overall and float(grade_overall) > 0:
            review.grades.append((Grade(type='overall', value=float(grade_overall), best=5.0)))

    pros = new_data.xpath('//p[starts-with(normalize-space(.), "-") and preceding-sibling::p[strong][1][contains(strong, "Hits:")]]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = pros = new_data.xpath('//p[starts-with(normalize-space(.), "-") and preceding-sibling::p[strong][1][contains(strong, "Misses:")]]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = rev_json.get('subheadline')
    if summary:
        review.add_property(type='summary', value=summary.strip())

    conclusion = new_data.xpath('//h3[contains(text(), "Verdict")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclsuion', value=conclusion)

    excerpt = new_data.xpath('//p[not(regexp:test(strong, "Hits:|Misses:|Price|RatingALSO READ|Specifications") or preceding::p[regexp:test(strong, "Hits:|Misses:|Price|RatingALSO READ|Specifications")] or preceding::h3[contains(text(), "Verdict")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
