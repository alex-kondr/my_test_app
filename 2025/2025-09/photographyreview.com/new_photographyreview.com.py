from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('http://www.photographyreview.com/'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-menu_header"]//li[contains(., "USER REVIEWS")]//li/a')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(context, cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//table[@id='desktoptable']/tbody")
    for prod in prods:
        product = Product()
        product.name = prod.xpath(".//li/a/text()").string()
        product.url = prod.xpath(".//li/a/@href").string()
        product.ssid = product.url.split('/')[-1].replace('.html', '')
        product.category = context['cat'].title()

        revs_cnt = prod.xpath('.//li/font[contains(text(), " Reviews")]/text()').string()
        if revs_cnt and int(revs_cnt.replace(' Reviews', '')) > 0:
            session.queue(Request(product.url), process_reviews, dict(product=product))

    next_url = data.xpath('//a[contains(., "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//table[@class="user-review-desktop"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('tr/td[@class="review-td-left header_sub_menu_sample"]/div[1]//text()').string(multiple=True)
        if date:
            review.date = date.strip('[ ]')

        author = rev.xpath('tr/td[@class="review-td-left header_sub_menu_sample"]/div[3]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grades = rev.xpath('.//tr[td[@class="rate"] and td[contains(., "RATING")]]')
        for grade in grades:
            grade_name = grade.xpath('td[contains(., "RATING")]//text()').string(multiple=True).replace('RATING', '').strip().title()
            grade_val = grade.xpath('td[@class="rate"]//text()').string(multiple=True)
            if 'overall' in grade_name.lower():
                review.grades.append(Grade(type='overall', value=float(grade_val), best=5.0))
            else:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        excerpt = rev.xpath('.//div[@class="user-review-header-content"]//text()').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('.//div[@class="user-review-header" and position() > 4]//text()').string(multiple=True)

        if excerpt:
            excerpt = excerpt.replace(u'\uFEFF', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[contains(., "Next")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
