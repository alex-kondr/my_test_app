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
    title = data.xpath("//h1[@class='noflir']//text()").string()

    product = Product()
    product.name = data.xpath("//h2//a//text()").string() or title
    product.url = context['url']
    product.category = 'Games'

    ssid = context['url'].split('-')[-1].strip(' /')
    if ssid.isdigit():
        product.ssid = ssid
    else:
        product.ssid = context['url'].split('/')[-3]

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
    review.title = title
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

    grade_overall = data.xpath("//div[@class='scoreSplit' and not(.//a)]//meter").first()
    if grade_overall:
        grade_val = grade_overall.xpath("@value").string()
        grade_max = grade_overall.xpath("@max").string()
        review.grades.append(Grade(type='overall', value=float(grade_val), best=float(grade_max)))

    grades = data.xpath('//div[@class="scoreSplit"]//a')
    for grade in grades:
        grade_name = grade.xpath('text()').string(multiple=True)
        grade_val = grade.xpath('meter/@value').string()
        if grade_name and grade_val and grade_val.isdigit() and float(grade_val) > 0:
            grade_name = grade_name.split('/ 10')[-1].strip()
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath("//div[@class='goodbad'][1]//text()").string(multiple=True)
    if pros:
        pros = pros.split('.')
        for pro in pros:
            pro = pro.strip(' +-*.:;•,–"')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@class='goodbad'][2]//text()").string(multiple=True)
    if cons:
        cons = cons.split('.')
        for con in cons:
            con = con.strip(' +-*.:;•,–"')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//h2[@class='intro']//text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//div[@id="page0"]|//body)/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
