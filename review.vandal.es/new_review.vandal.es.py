from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://vandal.elespanol.com/analisis/videojuegos"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='span4']/div[@class='caja300 afterclearer']")
    for rev in revs:
        name = rev.xpath("./a/@title").string()
        url = rev.xpath("./a/@href").string()
        cat = "Games|" + rev.xpath(".//div[@class='subtitulocaja afterclearer']//span/text()").string(multiple=True)
        session.queue(Request(url), process_review, dict(context, name=name, url=url, cat=cat))

    next_url = data.xpath("//a[@id='siguientelink']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath("//div[@class='titulojuego']/a[@class='linkversion']//text()").string() or context["name"]
    product.ssid = context["url"].split('/')[-1].split('#')[0]
    product.category = context["cat"]
    product.url = context["url"]
    product.manufacturer = data.xpath("//div[@class='fichatecnica']//li[contains(.,'Producción')]/a//text()").string()

    review = Review()
    review.title = context["name"]
    review.ssid = product.ssid
    review.type = "pro"
    review.url = context["url"]
    review.date = data.xpath("//span[@class='dtreviewed']/span/@title").string()

    authors = data.xpath("//div[@class='cuadro_autor_nombre']/a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    grades = data.xpath("//div[@class='mt15']/div[contains(@class,'celtatexto')]")
    for grade in grades:
        grade_name = grade.xpath(".//text()").string()
        grade_val = grade.xpath("(./following-sibling::div)[1]/div/div/@class").string().split("barra")[2]
        if grade_name != "Overall":
            review.grades.append(Grade(name=grade_name, value=int(grade_val), best=100))

    grade_overall = data.xpath("//div[contains(@class,'circuloanalisis_nota')]/text()[not(self::strong)]").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.').replace('%', '').replace("width:", '')
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=10.0))

    pros = data.xpath("//div[@class='span4 mb1']/h3[contains(.,'positivos')]/following-sibling::div")
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True).replace('+', '').replace('.', '').strip()
        if pro:
            review.add_property(type="pros", value=pro)

    cons = data.xpath("//div[@class='span4 mb1']/h3[contains(.,'negativos')]/following-sibling::div")
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True).replace("- ", '').replace('.', '').strip()
        if con:
            review.add_property(type="cons", value=con)

    conclusion = data.xpath("//span[@class='summary']/text()").string()
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[@class='textart']/p//text()").string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)
