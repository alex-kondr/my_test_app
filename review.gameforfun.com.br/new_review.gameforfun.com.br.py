from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://gameforfun.com.br/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[contains(@class, "link__link")]')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].replace('Review: ', '').replace('Review ', '').replace('Análise ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Games'

    platforms = data.xpath('//p[contains(text(), "nos jogos de")]/text()').string()
    if platforms:
        product.category += '|' + platforms.split('nos jogos de')[-1].strip().replace(', ', '/').replace(' e ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//h2[contains(@class, "heading-title") and contains(., "Por: ")]//text()').string()
    author_url = data.xpath('//h2[contains(@class, "heading-title") and contains(., "Por: ")]/a/@href').string()
    if author and author_url:
        author = author.replace('Por: ', '').strip()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.replace('Por: ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//input[@class="jet-form__field hidden-field" and contains(@name, "_value")]/@value').strings()
    if grade_overall:
        grade_overall = round(sum([float(grade) for grade in grade_overall]) / len(grade_overall))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    grades = data.xpath('//input[@class="jet-form__field hidden-field" and contains(@name, "_value")]')
    for grade in grades:
        grade_name = grade.xpath('@name').string().replace('_value', '').title()
        grade_val = grade.xpath('@value').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    summary = data.xpath('//div[contains(@class, "post-excerpt")]/div//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3)[contains(., "Conclusão")]/following-sibling::p[not(contains(., "e está disponível para") and b)]//text()').string(multiple=True)
    if conclusion and not summary:
        summary = data.xpath('//h2[contains(text(), "Nota")]/following::div[@class="elementor-widget-container"]/p//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

    if not conclusion:
        conclusion = data.xpath('//h2[contains(text(), "Nota")]/following::div[@class="elementor-widget-container"]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//h3)[contains(., "Conclusão")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="AreaConteudo"]/div/p[not(contains(., "e está disponível para") and b)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
