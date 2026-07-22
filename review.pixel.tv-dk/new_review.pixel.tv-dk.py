from agent import *
from models.products import *


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
    session.queue(Request('https://pixel.tv/category/gaming/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'Anmeldelse' in title:
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Spil'
    product.manufacturer = data.xpath('//tr[contains(td, "Udvikler") or contains(td, "Udgiver")]/td[not(contains(., "Udvikler") or contains(., "Udgiver"))]/text()').string()

    product.name = data.xpath('//tr[contains(td, "Titel")]/td[not(contains(., "Titel"))]/text()').string()
    if not product.name:
        product.name = context['title'].split('|')[-1].replace('Anmeldelse: ', '').replace('Anmeldelse', '').replace('anmeldelse', '').split('‘')[-1].split('’')[0].strip()

    platforme = data.xpath('//tr[contains(td, "Platform")]/td[not(contains(., "Platform"))]//text()').string(multiple=True)
    if platforme:
        product.category += '|' + platforme.replace('/', '\\').replace(', ', '/').split('(')[0].strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//header[contains(@class, "title")]//time[@itemprop="datePublished"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//header[contains(@class, "title")]//span[@class="author vcard" and not(contains(., "Pixel.TV"))]/text()').string()
    author_url = data.xpath('//header[contains(@class, "title")]//span[@class="author vcard"]/a[not(contains(@href, "/author/pixel-tv/"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//img/@src[contains(., "Pixel-Hjerte")]').string()
    if grade_overall:
        grade_overall = grade_overall.split('Pixel-Hjerte')[-1].replace('.webp', '')
        if grade_overall.isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[contains(strong/text(), "pixel-hjerter") or contains(strong/text(), "Karakter:")]/strong/text()[contains(., "/")]').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Karakter:', '').split('/')[0].strip()
            if grade_overall.isdigit() and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    conclusion = data.xpath('(//h2|//h3)[contains(., "Konklusion")]/following-sibling::p[not(contains(strong/text(), "pixel-hjerter") or contains(strong/text(), "Karakter:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(strong/text(), "ENDELIGE VURDERING:")]//text()[not(contains(., "ENDELIGE VURDERING:"))]|//p[contains(strong/text(), "ENDELIGE VURDERING:")]/following-sibling::p[not(contains(strong/text(), "pixel-hjerter"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//h3)[contains(., "Konklusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(strong/text(), "ENDELIGE VURDERING:")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(strong/text(), "pixel-hjerter") or contains(strong/text(), "Karakter:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
