from agent import *
from models.products import *


XCAT = ["Все статьи", "FAQ", "Институт оверклокинга", "Руководства", "События", "Сайт", "Всё про..."]


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://overclockers.ru/lab'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//div[contains(@class, 'content-menu')]//div[@class='ui horizontal list']/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    for rev in data.xpath("//div[@class='item article-wrap']/div[@class='content']"):
        title = rev.xpath("a//text()").string(multiple=True)
        url = rev.xpath("a/@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next = data.xpath("//div[@class='ui pagination menu']/a[@class='item next']/@href").string()
    if next:
        session.queue(Request(next), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = data.xpath('//a/@data-what-id').string()
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@href, '/author/')]/span/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating-value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[contains(@class, "sub-header")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Заключение")]/following-sibling::p[not(contains(., "По итогам обзора"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Заключение")]/preceding-sibling::p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:|По итогам обзора"))]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = excerpt.strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
