from agent import *
from models.products import *
import simplejson


XCAT = ['Aktuelles', 'Weltall', 'WhatsApp', 'Windows', 'Kreuzworträtsel']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.t-online.de/digital/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats_json = data.xpath('//script[@type="application/json"]/text()').string()
    if not cats_json:
        return

    cats_json = simplejson.loads(cats_json).get('props', {}).get('pageProps', {}).get('page', {}).get('stages', [])
    if cats_json:
        for cat_json in cats_json:
            cats = cat_json.get('header', {}).get('themenbereiche', [])
            if cats:
                for cat in cats:
                    name = cat.get('label')
                    url = 'https://www.t-online.de' + cat.get('href')

                    if name not in XCAT:
                        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))

                return


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[.//img[@title="Nächste Seite"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Passwort-Test: ', '').split(' im Test – ')[0].split(' im Test: ')[0].split(' im Vorab-Test: ')[0].replace('Test: ', '').replace(' im Test', '').replace(' im Praxistest', '').replace(' im Doppel-Test', '').replace(' im Alltagstest', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('id_', '')
    product.category = context['cat'].replace('Tests', 'Technik')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@data-tb-author and not(contains(., "t-online"))]/text()').string()
    author_url = data.xpath('//a[span[@data-tb-author and not(contains(., "t-online"))]]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2].replace('id_', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@data-testid, "ArticleBody")]/div/div/p[contains(@class, "font-bold")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@data-testid="StageLayout.StreamItem" and p[.//span[text()="Fazit"]]]/following::div[@data-testid="StageLayout.StreamItem"]/p[not(contains(@class, "font-bold"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@data-testid="StageLayout.StreamItem" and p[.//span[text()="Fazit"]]]/preceding::div[@data-testid="StageLayout.StreamItem"]/p[not(contains(@class, "font-bold"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@data-testid="StageLayout.StreamItem"]/p[not(contains(@class, "font-bold"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
