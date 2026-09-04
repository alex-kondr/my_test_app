from agent import *
from models.products import *
import HTMLParser
import simplejson


h = HTMLParser.HTMLParser()


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.fotografie.nl/boeken/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs_json = data.xpath('//script[contains(., "var slugs=")]/text()').string()
    if revs_json:
        revs_json = simplejson.loads(revs_json.split('var slugs=')[-1].split(';')[0])
        for rev in revs_json.values():
            url = 'https://www.fotografie.nl/post/' + rev
            session.queue(Request(url), process_review, dict(url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = title
    product.ssid = context['url'].split('/')[-1]
    product.category = 'Boeken'

    product.url = data.xpath('//a[contains(., "Bestel dit boek")]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//p[contains(., "Uitgever:")]/text()[contains(., "Uitgever:")]').string()
    if manufacturer:
        product.manufacturer = h.unescape(manufacturer).replace('Uitgever:', '').replace('&Amp;', '&').strip()

    ean = data.xpath('//p[contains(., "ISBN:")]//text()[contains(., "ISBN:")]').string(multiple=True)
    if ean:
        ean = ean.replace('ISBN:', '').strip()
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    rev_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

        author = rev_json.get('author', {}).get('name')
        if author and 'Redactie' not in author:
            review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('''//div[contains(@class, "article-content")]/p[not(regexp:test(., "Pagina's:|Uitgever:|Vertaling:|ISBN:"))]//text()''').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
