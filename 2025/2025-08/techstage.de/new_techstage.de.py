from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.heise.de/tests', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@data-component="TeaserLinkContainer"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url))

    if revs:
        next_page = context.get('page', 0) + 1
        next_url = 'https://www.heise.de/tests/load-more?moduleId=4287194&c={}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string(multiple=True)

    product = Product()
    product.name = title.replace('Test-Access-Point im Test: ', '').replace('KI im Test: ', '').split(' im Test')[0].split(' im Dauertest: ')[0].replace('Selbsttest: ', '').replace('Test: ', '').replace('Praxistest: ', '').replace('Im Test: ', '').replace('Almauftrieb: ', '').replace(' – Kurztests', '').replace('Kurztests: ', '').replace('Kurztest: ', '').split(': Praxis-Test ')[0].replace('Kurztest ', '').replace('Motorroller-Test ', '').replace(' im ersten Test', '').replace(' im Vergleichtest', '').replace(' im Vergleichstest', '').replace(' im Kurztest', '').replace('Kühlertest: ', '').replace('Test ', '').replace(' im Praxistest', '').split(' im Alltagstest​: ')[0].replace('Kameratest ', '').replace('Apple-Spieletests: ', '').replace('Vergleichstest: ', '').replace(' im Labortest', '').split(' im Kameratest: ')[0].replace('Kameratest: ', '').replace(' im OpenWrt-Test', '').split(' im Review: ')[0].replace('Praxis- und Labortest ', '').replace('Objektivtest: ', '').replace('Härtetest in der Arktis: ', '').replace('Spiele-Review: ', '').replace('Spielereview: ', '').replace(" im c't-Test", '').replace('Review ', '').replace('Spieletest ', '').replace(' im Beta-Test', '').replace(' getestet', '').replace(' Vergleichstest', '').replace(' im Dauertest', '').replace('Testkauf: ', '').replace(' im Hörtest', '').replace(' im Hands-on-Test', '').replace(' im Labor- und Praxistest', '').replace('Kurztests Mac-Apps: ', '').replace('Kurztests iOS-Apps: ', '').replace(' "im Test"', '').replace(' im Langzeittest', '').replace('Kurztests iPhone-Spiele: ', '').replace('Kurztests iPhone-Software: ', '').replace('Kurztests Mac-Software: ', '').replace('Kurztests Apple-Hardware: ', '').replace(' im großen Test', '').replace(' im Videotest', '').replace(' angetestet', '').replace(' im Fahrtest', '').replace(' im ausführlichen Test', '').replace(' ​im Test', '').replace(' im Langstreckentest', '').replace('Getestet: ', '').replace('Kurztests der Woche: ', '').replace('Angetestet: ', '').replace('Kurztests des Jahres: ', '').strip('  ')
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')
    product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//li[@class="creator__name"]')
    for author in authors:
        author_name = author.xpath('.//text()').string(multiple=True)
        author_url = author.xpath('a/@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1].split('-')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    summary = data.xpath('//p[contains(@class, "article-header")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="article-content"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
