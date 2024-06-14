from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.profesionalreview.com/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[@class="the-next-page"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Review en Español')[0].split('Review en español')[0].split('review en Español')[0].split('Review Español')[0].split('Review del')[0].split('– Review')[0].split(' review: ')[0].split('Review con')[0].split('Review técnico')[0].replace('Preview y primeras impresiones', '').replace('Review:', '').replace('Test de rendimiento de ', '').replace('¿El siguiente nivel? Review', '').replace('Unboxing y primeras impresiones (Preview)', '').replace('review en español (Análisis completo)', '').replace('(Análisis completo)', '').replace(' Preview', '').replace(' Review', '').replace('Review ', '').replace(' review', '').strip(' ,')
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Tecnica'

    product.url = data.xpath('//div[@class="aawp-product__inner"]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]/h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style[contains(., "width")]').string()
        if grade_overall:
            grade_overall = float(grade_overall.strip('width: %')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]//span/@title').string()
        if grade_overall:
            grade_overall = grade_overall.split()[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('h5//text()[normalize-space()]').string()

        if ' - ' in grade_name:
            grade_name, grade_val = grade_name.split(' - ')
            grade_name = grade_name.strip()
            grade_val = grade_val.strip(' %')
        else:
            grade_val = float(grade.xpath('.//span[contains(@style, "width")]/@style').string().strip('width: %')) / 20

        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    conclusion = data.xpath('//h2[contains(., "conclusión") or contains(., "conclusiones")]/following-sibling::p[not(@style or contains(., "El equipo de Profesional Review le otorga") or contains(., "Última actualización"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="review-short-summary"]//p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "conclusión")]/preceding-sibling::p[not(@style)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content entry clearfix"]/p[not(@style or contains(., "El equipo de Profesional Review le otorga"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
