from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.greenskeeper.org/productreviews/reviews.cfm', use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="title"]//a[text()]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(name=name, url=url))

    next_url = data.xpath('//a[contains(., "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//td[@class="pathnavagation"]//a[not(contains(., "Reviews"))]/text()').join('|')

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs_excerpt = context.get('revs_excerpt', [])
    page_dublicate = False

    revs = data.xpath('//div[@id="listreviews"]//tr[.//div[@class="review"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[@class="date"]/text()').string()
        if date:
            review.date = date.split(' ', 1)[-1]

        author = rev.xpath('.//div[@class="name"]//text()[not(contains(., "Read ALL"))]').string()
        author_url = rev.xpath('.//div[@class="name"]//a[not(contains(., "Read ALL"))]/@href').string()
        if author and author_url:
            author_ssid = author_url.split('=')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//tr[td[@class="labels" and contains(., "Overall")]]//img[contains(@src, "starfull")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.xpath('.//tr[td[@class="labels" and not(contains(., "Overall"))]]')
        for grade in grades:
            grade_name = grade.xpath('.//td[@class="labels"]//text()').string(multiple=True)
            grade_val = grade.xpath('count(.//img[contains(@src, "starfull")])')
            if grade_name and grade_val:
                review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

        title = rev.xpath('.//div[@class="title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            if context.get('page') and excerpt in revs_excerpt:
                page_dublicate = True
                break

            revs_excerpt.append(excerpt)
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if len(revs) == 15 and not page_dublicate:
        next_page = context.get('page', 1) + 1
        next_url = product.url + '?page=' + str(next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product, page=next_page, revs_excerpt=revs_excerpt))

    elif product.reviews:
        session.emit(product)
