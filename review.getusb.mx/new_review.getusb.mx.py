from agent import *
from models.products import *
import HTMLParser


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://spanish.getusb.info/', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="topic-grid"]/a[p]')
    for cat in cats:
        name = cat.xpath('h3/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "article")]/h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = h.unescape(context['title']).split(' - ')[0].split(' – ')[0].replace('Reseña: ', '').replace('AnÃ¡lisis: ', '').replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tecnología'

    review = Review()
    review.type = 'pro'
    review.title = h.unescape(context['title']).replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//p[@class="post-date"]/text()').string()

    summary = data.xpath('//p[@class="post"]//text()').string()
    if summary:
        summary = h.unescape(summary).replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "conclusión") or contains(., "Conclusión")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = h.unescape(conclusion).split("Trackback")[0].split("Tags:")[0].replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "conclusión") or contains(., "Conclusión")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "text-large")]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).split("ConclusiÃ³n")[0].split('CONCLUSIÃ“N')[0].split("Trackback")[0].split("Tags:")[0].replace('Veamos algunos:', '').replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
