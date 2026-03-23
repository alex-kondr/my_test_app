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
        url = rev.get('url')

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

    summary = rev_json.get('subheadline')
    if summary:
        review.add_property(type='summary', value=summary.strip())

    excerpts = rev_json.get('cards', [{}])[0].get('story_elements', [])
    if excerpts:
        excerpt_data = ''.join([excerpt.get('text', '').strip() for excerpt in excerpts if '<p>' in excerpt.get('text')])

        excerpt = excerpt_data.replace('<p>', '').replace('</p>', '').replace('<em>', '').replace('</em>', '').replace('- muzaffarrizvi@khaleejtimes.com', '').strip()

        if '<strong>Stars</strong>:' in excerpt:
            excerpt, grade_overall = excerpt.split('<strong>Stars</strong>:')

            grade_overall = grade_overall.split('/')[0]
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if 'CONS' in excerpt:
            excerpt, cons = excerpt.split('CONS')

            cons = cons.split('\t')
            for con in cons:
                con = con.strip(' +-*.;•–>')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        if 'PROS' in excerpt:
            excerpt, pros = excerpt.split('PROS')

            pros = pros.split('\t')
            for pro in pros:
                pro = pro.strip(' +-*.;•–>')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        excerpt = excerpt.replace('<strong>', '').replace('</strong>', '').replace('\t', '').split('Specifications')[0].strip()
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
