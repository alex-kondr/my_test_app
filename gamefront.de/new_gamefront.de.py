from agent import *
from models.products import *
import simplejson


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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://gamefront.de/reviews/revs.html', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

# no next page


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('(')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = 'Spiele'

    platforme = data.xpath('(//p|//td)[contains(., "System:")]/text()[contains(., "System:")]').string()
    if platforme:
        product.category += '|' + platforme.split('System:')[-1].strip()

    manufacturer = data.xpath('(//p|//td)[contains(., "Entwickler:")]/text()[contains(., "Entwickler:")]').string()
    if not manufacturer:
        manufacturer = data.xpath('//b[contains(., "Entwickler")]/following-sibling::text()[1]').string()

    if manufacturer:
        product.manufacturer = manufacturer.split('Entwickler:')[-1].strip(' :')

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1//text()').string(multiple=True) or context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    grade_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if grade_json:
        grade_overall = simplejson.loads(grade_json).get('reviewRating', {}).get('ratingValue', 0)
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    summary = data.xpath('//h2//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//p[@class="vv"]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//p[@class="text"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[@class="xx"]/text()|//p[@class="xx"]/*[not(self::table)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//font[@face and not(font)]//text()').string(multiple=True)

    if excerpt:
        if 'Fazit:' in excerpt:
            excerpt, conclusion = excerpt.split('Fazit:')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
