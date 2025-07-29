from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://nordic.ign.com/article/review', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3//a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' - ')[0].replace('Early Access Review', '').replace('Review in Progress', '').replace('- Review', '').replace('-Review', '').replace('Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath('//div[@class="object-subinfo"]/span[@class="txt"]/text()').string()

    platforms = data.xpath('//body[.//@class="platform" and not(.//div)]/preceding-sibling::head[1]/title/text()').join('/')
    if platforms:
        product.category = 'Games|' + platforms

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="author-names"]/span[@class="reviewer hcard"]//text()').string(multiple=True)
    author_url = data.xpath('//div[@class="author-names"]/span[@class="reviewer hcard"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review"]//span[@class="side-wrapper side-wrapper hexagon-content"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//h3[@id="id_deck"]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3[regexp:test(text(), "Verdict", "i")])[last()]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="details"]/div[contains(@id, "id_keyword")]//text()').string(multiple=True)

    if conclusion:
        conclusion = re.sub(r'<[^<>]+>', '', conclusion).replace('Verdict: ', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@itemprop="articleBody"]/p[not(preceding::h3[regexp:test(text(), "Verdict", "i")] or preceding-sibling::*[1][@class="vplayer" and iframe[not(contains(@data-src, "https://widgets.ign.com"))]] or regexp:test(., "Read the full|Score:"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<[^<>]+>', '', excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
