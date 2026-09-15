from agent import *
from models.products import *
import time
import random


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("http://multiplayer.it/articoli/recensioni/", use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    for rev in data.xpath("//h3/a"):
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath("//li[@class='page-item'][last()]/a/@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    title = data.xpath("//h1//text()").string(multiple=True)

    product = Product()
    product.ssid = context['url'].split('/')[-1].split('.html')[0]
    product.url = context['url']
    product.category = "Giochi"

    product.name = data.xpath('//div[contains(@class, "gamecard__title")]//text()').string(multiple=True)
    if not product.name:
        product.name = title.split(': ')[0].split(", ")[0]

    platforme = data.xpath('//small[contains(text(), "Versione testata")]/following-sibling::b/text()').string()
    if platforme:
        product.category += "|" + platforme

    review = Review()
    review.title = title
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//*[@id='_article_pub_date']//text()").string()

    author = data.xpath('//span[@class="article__header__type-author"]/*[not(contains(., "RECENSIONE"))]/text()').string()
    author_url = data.xpath('//span[@class="article__header__type-author"]/*[not(contains(., "RECENSIONE"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-4]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("(//p[contains(@class,'article__verdict__boxes__vote')])[1]//text()").string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "box-multi")]/div[contains(@class, "verdict__boxes__vote")]/strong/text()').string()

    if grade_overall and grade_overall[0].isdigit():
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grade_users = data.xpath('//div[contains(@class, "box-user")]/div[contains(@class, "verdict__boxes__vote")]/strong/text()').string()
    if grade_users and grade_users[0].isdigit():
        review.grades.append(Grade(name='Lettori', value=float(grade_users), best=10.0))

    pros = data.xpath("//div[contains(@class, 'article__pros-cons__pros')]/ul/li")
    for pro in pros:
        pro = pro.xpath(".//text()").string()
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[contains(@class, 'article__pros-cons__cons')]/ul/li")
    for con in cons:
        con = con.xpath(".//text()").string()
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1 and pro != 'No':
                review.add_property(type='cons', value=con)

    summary = data.xpath("//p[contains(@class, 'subtitle')]//text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//p[contains(@class, 'article__verdict__description')]//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='article__content']//p[not(@class)]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
