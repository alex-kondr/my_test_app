from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.gamereactor.es/analisis'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "leftbox")]/a/@href')
    for prod in prods:
        url = prod.string()
        session.queue(Request(url), process_product, dict(url=url))

    next_url = data.xpath("//td[@class='next']/a/@href").string()
    if prods and next_url:
        session.queue(Request(next_url), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath("//h2//a//text()").string()
    product.ssid = context['url'].split('/')[-2]
    product.url = context['url']
    product.category = 'Games'

    cat = data.xpath("(//ul[@class='infobox']//li[contains(.,'Plataforma')]//text())[2]").string()
    if not cat:
        cat = data.xpath("(//ul[@class='infobox']//li[contains(.,'Probado en')]//text())[2]").string()

    if cat:
        product.category += '|' + cat.split(',')[0].strip()

    product.manufacturer = data.xpath("//div[@class='boxbody']//li[contains(.,'Editor')]//a//text()").string()
    if not product.manufacturer:
        product.manufacturer = data.xpath("//div[@class='boxbody']//li[contains(.,'Desarrollador')]//a//text()").string()

    review = Review()
    review.type = 'pro'
    review.title = data.xpath("//h1[@class='noflir']//text()").string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath("//time/@datetime").string()
    if date:
        review.date = date.split('CEST')[0]

    authors = data.xpath("//li[contains(@class, 'publishAuthor')]//a")
    for author in authors:
        author_url = author.xpath("@href").string()
        author_name = author.xpath(".//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))

    grade = data.xpath("//div[@class='scoreSplit']//meter").first()
    if grade:
        grade_val = grade.xpath("@value").string()
        grade_max = grade.xpath("@max").string()
        review.grades.append(Grade(type='overall', value=float(grade_val), best=float(grade_max)))

    pros = data.xpath("//div[@class='goodbad'][1]//text()").string(multiple=True)
    if pros:
        pros = pros.split('.')
        for value in pros:
            review.add_property(type='pros', value=value.strip())

    cons = data.xpath("//div[@class='goodbad'][2]//text()").string(multiple=True)
    if cons:
        cons = cons.split('.')
        for value in cons:
            review.add_property(type='cons', value=value.strip())

    summary = data.xpath("//h2[@class='intro']//text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//div[@id="page0"]|//body)/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
