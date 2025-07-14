from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gamesunit.de/tag/Review', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="Item"]')
    for rev in revs:
        rev_id = rev.xpath('@id').string()
        title = rev.xpath('h1/a/text()').string()
        url = rev.xpath('h1/a/@href').string()

        if 'preview' not in title.lower() and 'review' in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = 'https://www.gamesunit.de/fetchArticle.ashx?lastaid={}'.format(rev_id)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist_next, dict())


def process_revlist_next(data, context, session):
    revs = simplejson.loads(data.content.replace('	', '')).get('a', [])
    for rev in revs:
        rev_id = rev.get('id')
        timestamp = rev.get('timestamp')
        title = h.unescape(rev.get('head'))
        url = 'https://www.gamesunit.de' + rev.get('link')

        if 'preview' not in title.lower() and 'review' in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    if revs:
        next_url = 'https://www.gamesunit.de/fetchArticle.ashx?lastaid=ArticleId_{timestamp}-{rev_id}'.format(timestamp=timestamp, rev_id=rev_id)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist_next, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'Review: |\[.+\]| im Test', '', re.split(r'Review ?\([\w\-\s]+\)[ :|]?', context['title'].split(' - ')[0].split('/ Review')[0].split(': Review')[0], flags=re.UNICODE)[-1], flags=re.UNICODE).strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')

    category = re_search_once(r'\(.+\)', context['title'])
    if category:
        product.category = category[0].strip('( )')
    else:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//h4[contains(., " von")]/text()').string()
    if date:
        review.date = date.split(', von')[0]

    author = data.xpath('//h4[contains(., " von")]//text()').string(multiple=True)
    author_url = data.xpath('//h4[contains(., " von")]/a/@href').string()
    if author:
        author = author.split(', von')[-1].strip()
        if author and author_url:
            author_ssid = author_url.split('/')[-1].replace('.html', '')
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(., "Fazit")]]//text()[not(contains(., "Fazit"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(b[contains(., "Spezifikationen")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="Item"]/p[not(contains(., "Fazit"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
