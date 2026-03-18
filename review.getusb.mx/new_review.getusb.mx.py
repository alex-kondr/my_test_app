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
    session.queue(Request('https://spanish.getusb.info/category/analisis-usb/', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath("//h1[@class='uk-article-title']/a")
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, max_age=0), process_review, dict(url=url, title=title))

    next_url = data.xpath('//a[contains(i/@class, "double-right")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - ')[0].split(' – ')[0].replace('AnÃ¡lisis: ', '').replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath("//span[@class='tm-article-category uk-visible-large']/a[1]//text()").string() or 'Analisis USB'

    review = Review()
    review.type = 'pro'
    review.title = h.unescape(context['title']).replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
    review.ssid = product.ssid
    review.url = product.url
    review.date = data.xpath("//span[@class='tm-article-date']/time/@datetime").string()

    author = data.xpath('//span[contains(@class, "article-author")]//text()').string()
    author_url = data.xpath('//span[contains(@class, "article-author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[@class="post"]//text()').string()
    if summary:
        summary = h.unescape(summary).replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//strong[regexp:test(normalize-space(.), 'ConclusiÃ³n|CONCLUSIÃ“N')]/following-sibling::text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//p[strong[regexp:test(normalize-space(.), 'ConclusiÃ³n|CONCLUSIÃ“N')]]/following-sibling::text()|//p[strong[regexp:test(normalize-space(.), 'ConclusiÃ³n|CONCLUSIÃ“N')]]/following-sibling::blockquote//text()").string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).split("Trackback")[0].split("Tags:")[0].replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//main[contains(@class, "content")]/article|//main[contains(@class, "content")]/article/a|//main[contains(@class, "content")]/article/strong)/text()|//main[contains(@class, "content")]/article/p[not(@class)]//text()|//main[contains(@class, "content")]/article/div/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).split("ConclusiÃ³n")[0].split('CONCLUSIÃ“N')[0].split("Trackback")[0].split("Tags:")[0].replace('Veamos algunos:', '').replace(u'�', '').replace(u'Ã¡', u'á').replace(u'Ã©', u'é').replace(u'Ã³', u'ó').replace(u'Ã­', u'í').replace(u'Â', u' ').replace(u'â€œ', u'“').replace(u'â€', u'”').replace(u'\x9D', '”').replace(u'hiceron', u'hicieron').replace(u'apoyo', u'apoyó').replace(u'Ã\x81', u'Á').replace(u'Ã±', u'ñ').replace(u'Ã\x8D', u'Í').replace('  ', ' ').replace(u'Ã¼', u'ü').replace(u'Ã¶', u'ö').replace(u'Ã\x9c', u'Ü').replace(u'Ã\x96', u'Ö').replace(u'Ã\x9f', u'ß').replace(u'Ãº', u'ú').replace(u'Ã“', u'Ó').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
