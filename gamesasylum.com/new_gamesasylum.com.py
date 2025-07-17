from agent import *
from models.products import *
import re
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.gamesasylum.com/category/review/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = h.unescape(rev.xpath('text()').string()).strip().replace(u'Ã©', 'e').replace(u'Ã¡', 'a').replace(u'â€“', '').replace(u'â€˜', "’").replace(u'â€¦', '').replace(u'â€œ', '').replace(u'â€�', '').replace(u'Ð±', '').replace(u'Ð°', '').replace(u'Ð½', '').replace(u'Ðº', '').replace(u'Ð²', '').replace(u'Ñ�', '').replace(u'ÑŽ', '').replace(u'Ñ€', '').replace(u'Ñƒ', '').replace(u'Ã¶', '').replace(u'Ã¼', '').replace(u'Ãœ', '').replace(u'Ã§', '').replace(u'Ã±', '').strip()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'–?[  â€“¦œ�]+review( \(.+\))?|\(.+\)| review|\[.+\]', '', context['title'], flags=re.I|re.U).strip(' –')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')

    category = re.search(r'\(.+\)', context['title'])
    if category:
        product.category = category.group().strip('( )')
    else:
        product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score-value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    excerpt = data.xpath('//div[@class="entry-content"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).strip().replace(u'Ã©', 'e').replace(u'Ã¡', 'a').replace(u'â€“', '').replace(u'â€˜', "’").replace(u'â€¦', '').replace(u'â€œ', '').replace(u'â€�', '').replace(u'Ð±', '').replace(u'Ð°', '').replace(u'Ð½', '').replace(u'Ðº', '').replace(u'Ð²', '').replace(u'Ñ�', '').replace(u'ÑŽ', '').replace(u'Ñ€', '').replace(u'Ñƒ', '').replace(u'Ã¶', '').replace(u'Ã¼', '').replace(u'Ãœ', '').replace(u'Ã§', '').replace(u'Ã±', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
