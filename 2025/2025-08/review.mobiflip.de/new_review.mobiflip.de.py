from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.mobiflip.de/thema/testberichte/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' vs. ' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Flaggschiff-Test: ', '').replace('Im Test: ', '').split(' im Test: ')[0].split(' im Test ')[0].split(': Mein Test ')[0].split(' im ersten Test: ')[0].split(' Langzeit-Test: ')[0].split(' im Langzeittest: ')[0].split(' Test: ')[0].split(' Test nach ')[0].split(' Kurztest ')[0].split(': Test ')[0].replace('Technik im Alltag: ', '').replace(' im persönlichen Langzeit-Test', '').replace(' im ausführlichen Test', '').replace(' im Härtetest', '').replace(' im Test', '').replace('Meine Baby-Testreihe: ', '').replace(' im Langzeit-Test', '').replace(' im kurzen Test', '').replace(' im ersten Test', '').replace(' im Langzeittest', '').replace(' im Alltagstest', '').replace('Mein o2-Netztest: ', '').replace('Testbericht: ', '').replace(' Testbericht', '').replace('Test: ', '').replace('Kurztest: ', '').replace(' mit MusicCast getestet', '').replace(' im Outdoor-Test', '').replace(' vorgestellt und getestet', '').replace(' getestet', '').replace(' im Kurztest', '').replace(' im Dauertest', '').replace(' im knallharten Selfietest', '').replace(' zum Test eingetroffen', '').replace(' im Videotest', '').replace(' Test', '').replace('Testbericht ', '').replace(' im Praxistest', '').replace(' Kurztest', '').replace(' im Kamera-Test', '').replace(' (Video)', '').replace(' im Lesertest', '').replace('Praxistest: ', '').replace('Getestet: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//span[@class="kurzspancatsingle" and not(regexp:test(., "Testberichte"))]/text()').string() or 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author-name")]//text()').string()
    author_url = data.xpath('//span[contains(@class, "author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[regexp:test(., "fazit", "i")]/following-sibling::p[not(.//span[@class="sharep-short-star"])]//text()[not(contains(., "tl;dr"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "fazit", "i")]/preceding-sibling::p[not(.//span[@class="sharep-short-star"])]//text()[not(contains(., "tl;dr"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p|//li)[not(@class or @id or preceding::*[@id="comments"] or .//span[@class="sharep-short-star"])]/span[@class="post-info-text" and text()]//text()[not(contains(., "tl;dr"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
