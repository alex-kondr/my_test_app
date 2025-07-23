from agent import *
from models.products import *
import re


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://atomix.vg/seccion/resenas/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h1[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Review – ', '').replace('Review – ', '').replace('Review- ', '').replace('Review — ', '').replace(' – Review', '').replace('REVIEW – ', '').replace('REVIEW ', '').replace('Reseña: ', '').replace('Review: ', '').replace('Review – ', '').replace('REVIEW — ', '').replace('Videoreseña – ', '').replace('Review– ', '').replace('REVIEW- ', '').replace(' reviews', '').replace('REVIEW: ', '').replace('Video review – ', '').replace('Reseña – ', '').replace('Reseña Indie: ', '').replace('RESEÑA: ', '').replace('RESEÑA – ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Juegos'
    product.manufacturer = data.xpath('//span[h1[normalize-space(text())="DESARROLLADOR"]]/p/text()').string()

    platforms = data.xpath('//span[h1[normalize-space(text())="PLATAFORMA"]]/p/text()').string()
    if platforms:
        product.category += '|' + platforms.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//img[contains(@alt, "score")]/@alt').string()
    if grade_overall:
        grade_overall = re.search(r'\d+', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group()[:2]
            if len(grade_overall) == 1:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
            else:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    conclusion = data.xpath('(//p[contains(., "En conclusión,") and @data-end and not(@data-is-only-node="")]|//p[contains(., "En conclusión,")]/following-sibling::p[@data-end and not(@data-is-only-node="")])[not(iframe[contains(@src, "https://www.youtube.com")])]//text()[not(contains(., "En conclusión,"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(., "En conclusión,")]|//p[contains(., "En conclusión,")]/following-sibling::p)[not(iframe[contains(@src, "https://www.youtube.com")])]//text()[not(contains(., "En conclusión,"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[.//img[contains(@alt, "score")]]|//p[.//img[contains(@alt, "score")]]/following-sibling::p)[not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "En conclusión,")]/preceding-sibling::p[@data-end and not(@data-is-only-node="")][not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "En conclusión,")]/preceding-sibling::p[not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//img[contains(@alt, "score")]]/preceding-sibling::p[not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-text")]/p[@data-end and not(@data-is-only-node="")][not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-text")]/p[not(iframe[contains(@src, "https://www.youtube.com")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
