#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


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


def RequestProds(page):
    options = "-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) Gecko/20100101 Firefox/84.0' -H 'Accept: */*' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' --compressed -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://www.freetogame.com' -H 'Connection: keep-alive' -H 'Referer: https://www.freetogame.com/games' -H 'TE: Trailers' --data-raw 'page=" + str(page) + "&userLoggedIn=&platform=&category_id=0&sort_by=ORDER BY featured DESC, YEAR(release_date) DESC, MONTH(release_date) DESC, featured_widgets DESC'"
    r = agent.Request('https://www.freetogame.com/ajax/ajax_load_games', use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(RequestProds(1), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//h3/a[contains(@class, "card-title")]')
    for prod in prods:
        url = prod.xpath('@href').string()
        if url and not session.seen(url):
            session.queue(Request(url), process_product, dict(url=url))

    if prods:
        page = context.get('page', 1) + 1
        session.queue(RequestProds(page), process_prodlist, dict(page=page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1//text()').string(multiple=True)
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('/')[-1]
    product.category = 'Games'
    product.manufacturer = data.xpath('//div[span[contains(text(), "Developer")]]/text()').string(multiple=True)

    platform = data.xpath('//div[span[contains(text(), "Platform")]]/text()').string(multiple=True)
    if platform:
        product.category += '|' + platform

    genre = data.xpath('//div[span[contains(text(), "Genre")]]/text()').string(multiple=True)
    if genre:
        product.category += '|' + genre

    revs = data.xpath('//div[@class="reviews"]//div[@class="deep-dark card-body"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('span[@class="timestamp small text-muted"]//text()').string()

        author = rev.xpath('.//span[@class="username"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath('div[@class="body"]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip()) > 1:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
