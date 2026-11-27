#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def RequestPost(page):
    options = "-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) Gecko/20100101 Firefox/84.0' -H 'Accept: */*' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' --compressed -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://www.freetogame.com' -H 'Connection: keep-alive' -H 'Referer: https://www.freetogame.com/games' -H 'TE: Trailers' --data-raw 'page=" + str(page) + "&userLoggedIn=&platform=&category_id=0&sort_by=ORDER BY featured DESC, YEAR(release_date) DESC, MONTH(release_date) DESC, featured_widgets DESC'"
    r = agent.Request('https://www.freetogame.com/ajax/ajax_load_games', use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    page = 1
    session.queue(RequestPost(page), process_prodlist, dict(page=page))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//a[@class='stretched-link no-underline']")
    prods_count = 0
    for prod in prods:
        url = prod.xpath("@href").string()
        if url and not session.seen(url):
            prods_count += 1
            session.queue(Request(url), process_product, dict(url=url))
    
    if prods_count > 0:
        page = context['page'] + 1
        session.queue(RequestPost(page), process_prodlist, dict(page=page))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = data.xpath("//div[@class='row']/div[@class='col-md-8']/h1//text()").string()
    product.ssid = context['url'].split('/')[-1]
    product.category = 'Games'
    product.url = context['url']

    revs = data.xpath("//div[@class='reviews']//div[@class='deep-dark card-body']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.date = rev.xpath("span[@class='timestamp small text-muted']//text()").string()
        
        author_name = rev.xpath(".//span[@class='username']//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        excerpt = rev.xpath("div[@class='body']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        
            review.ssid = product.ssid + '-' + review.date + '-' + author_name
            product.reviews.append(review)
    
    if product.reviews:
        session.emit(product)
