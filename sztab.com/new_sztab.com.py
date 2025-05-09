from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("http://www.sztab.com/recenzje-1.html"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//span[@class='al2']")
    for rev in revs:
        name = rev.xpath("a/text()").string()
        date = rev.xpath("preceding-sibling::span[@class='al1'][1]/text()").string()
        url = rev.xpath("a/@href").string()
        session.queue(Request(url), process_review, dict(url=url, name=name, date=date))

    page = context.get('page', 1) + 1
    next_url = data.xpath("//div[@id='links']/a[contains(@href, 'recenzje-" + str(page) + ".html')]/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(page=page))


def process_review(data, context, session):
    product= Product()
    product.name = context["name"]
    product.url = context['url']
    product.ssid = context['url'].split(',')[-1].replace('.html', '')
    product.category = 'Games'
    product.manufacturer = data.xpath('//b[contains(., "Producent:")]/following-sibling::text()').string()

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    review.date = context["date"]

    author = data.xpath('//div[@id="game_info"]/a/text()').string()
    author_url = data.xpath('//div[@id="game_info"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))

    grades = data.xpath('//div[@class="rating"]')
    for grade in grades:
        grade_name = grade.xpath('text()[not(regexp:test(., "GŁOSUJ|procent"))]').string(multiple=True).title()
        grade_val = grade.xpath('span/text()').string().replace('%', '')
        if grade_name and grade_val and grade_val.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100))

    pros = data.xpath('//div[@id="game_description"]/b[contains(., "ZALETY:")]/following-sibling::text()[not(preceding-sibling::b[contains(., "WADY:")])][normalize-space(.)]')
    for pro in pros:
        pro = pro.string().strip(' \n+-.,')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@id="game_description"]/b[contains(., "WADY:")]/following-sibling::text()[preceding-sibling::b[1][contains(., "WADY:")]][normalize-space(.)]')
    for con in cons:
        con = con.string().strip(' \n+-.,')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath("//div[@id='game_teaser']/text()").string()
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[@id="game_description"]//text()[contains(., "Podsumowując,")]').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Podsumowując,', '').strip(' \n+-.,').title()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@id="game_description"]//text()[contains(., "Podsumowując,")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="game_description"]/b[contains(., "ZALETY:")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="game_description"]/b[contains(., "WADY:")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="game_description"]/b[contains(., "Autor:")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="game_description"]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
