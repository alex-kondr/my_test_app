from agent import *
from models.products import *
import time
import random


def run(context, session):
    session.queue(Request("https://vandal.elespanol.com/analisis/videojuegos"), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(random.uniform(1, 3))

    revs = data.xpath("//div[@class='span4']/div[@class='caja300 afterclearer']")
    for rev in revs:
        title = rev.xpath('.//div[contains(@class, "titulo")]/text()').string()
        url = rev.xpath("a/@href").string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.url = context["url"]
    product.ssid = product.url.split('/')[-1].split('#')[0]
    product.category = 'Juegos'

    product.name = data.xpath('//div[@itemprop="name"]/a/text()').string()
    if not product.name:
        product.name = context['title'].replace(' - Análisis', '').strip()

    platforms = data.xpath('//td[@class="tablaplataformas"]/a/img/@alt').join('/')
    if platforms:
        product.category += '|' + platforms

    genres = data.xpath('//div[contains(text(), "Género/s:")]/a/text()').join('/')
    if genres:
        product.category += '|' + genres

    manufacturer = data.xpath("(//div[@class='fichatecnica']//li[contains(.,'Producción')])[1]//text()").string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.replace('Producción', '').strip(' .:').title()

    review = Review()
    review.type = "pro"
    review.title = data.xpath('//h1[@class="item"]//text()').string(multiple=True)
    review.url = context["url"]
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("(//div[@class='cuadro_autor_nombre']|//span[@itemprop='author' and .//text()])//text()").string(multiple=True)
    author_url = data.xpath("(//div[@class='cuadro_autor_nombre']|//span[@itemprop='author' and .//text()])//a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("//div[contains(@class,'circuloanalisis_nota')]/text()[not(self::strong)]").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.').replace('%', '').replace("width:", '').strip()
        if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=10.0))

    grades = data.xpath("//div[@class='mt15']/div[contains(@class,'celtatexto')]")
    for grade in grades:
        grade_name = grade.xpath(".//text()").string()
        grade_val = grade.xpath("(./following-sibling::div)[1]/div/div/@class").string().split("barra")[2]
        if grade_name != "Overall":
            review.grades.append(Grade(name=grade_name, value=int(grade_val), best=100))

    pros = data.xpath("//div[contains(h3,'positivos')]/div")
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type="pros", value=pro)

    cons = data.xpath("//div[contains(h3,'negativos')]/div")
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type="cons", value=con)

    summary = data.xpath('//span[@class="summary"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusión")]/following-sibling::p[not(contains(i, "Hemos analizado este juego"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(h3, "En resumen")]/div//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusión")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="reviewBody"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'�', '').strip()
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
