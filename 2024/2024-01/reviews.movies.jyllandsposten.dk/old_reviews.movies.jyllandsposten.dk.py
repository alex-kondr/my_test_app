from agent import *
from models.products import *
import simplejson
from datetime import datetime


def run(context, session):
    session.queue(Request('https://jyllands-posten.dk/kultur/film/?widget=article&widgetId=7997790&subview=ajaxList&templateName=gridCol620&showBreaker=false&shown=0&pageSize=99&_=1590243668666', use='curl'), process_revlist, dict(index=0))


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='article-teaser__heading']//a")
    for rev in revs:
        url = rev.xpath("@href").string()
        title = rev.xpath(".//text()").string(multiple=True)
        session.queue(Request(url, use='curl'), process_review, dict(url=url, title=title))

    if len(revs) >= 99:
        context['index'] += len(revs)
        next_page = 'https://jyllands-posten.dk/kultur/film/?widget=article&widgetId=7997790&subview=ajaxList&templateName=gridCol620&showBreaker=false&shown=' + str(context['index']) + '&pageSize=99&_=1590243668666'
        session.queue(Request(next_page, use='curl'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-3][3:]
    product.category = context['url'].split('/')[-4]
    product.url = context['url']

    rev_url = 'https://jyllands-posten.dk/api/articles?ids=' + product.ssid
    session.do(Request(rev_url, use='curl', force_charset='utf-8'), process_reviewjson, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviewjson(data, context, session):
    product = context['product']

    if data.content[0:2] == "{}":
        resp = simplejson.loads(data.content[4:])
    else:
        resp = simplejson.loads(data.content)

    revs = resp['_embedded']['articles']
    for rev in revs:
        review = Review()
        review.title = rev['rubrik']
        review.ssid = product.ssid
        review.type = 'pro'
        review.url = product.url

        date_stamp = rev['publishedDate']
        review.date = datetime.utcfromtimestamp(date_stamp / 1000).strftime('%d.%m.%Y')

        grade = int(rev['ratings']['top'])
        if grade < 0:
            grade = 0
        review.grades.append(Grade(type="overall", value=grade, best=6))

        author = rev['altAuthor'][3:-4]
        if not author:
            author = rev['byline'][0]['name']
        if author:
            review.authors.append(Person(name=author, ssid=author))

        summary = rev['underRubrik']
        review.properties.append(ReviewProperty(type='summary', value=summary))

        excerpt_in_json = rev['bodyTextParts'][0][0]
        excerpt_html = data.parse_fragment(excerpt_in_json.get('html', ''))
        excerpt = excerpt_html.xpath('//text()').string(multiple=True)
        if not excerpt:
            excerpt_in_json = rev['bodyTextParts'][0][1]
            excerpt_html = data.parse_fragment(excerpt_in_json.get('html', ''))
            excerpt = excerpt_html.xpath('//text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
            product.reviews.append(review)
