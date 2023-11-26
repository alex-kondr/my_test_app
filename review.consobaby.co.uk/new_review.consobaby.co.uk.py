from agent import *
from models.products import *


XCAT = ["Free product tests"]
XPROSCONS = ['-', 'no', 'na', 'a',  'none', 'unavailable', 'hard', 'n/a', 'n\a']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.consobaby.co.uk"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[contains(@class, "products mobile-show-in-sidebar")]')
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True).title()

        if name not in XCAT:
            sub_cats = cat.xpath('div[@class="child"]/ul/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/span[not(@class)]/text()').string().title()

                sub_cats1 = sub_cat.xpath('ul/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('span[not(@class)]/text()').string()
                        url = sub_cat1.xpath("@href").string()
                        session.queue(Request(url + '?dir=desc&order=review'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url + '?dir=desc&order=review'), process_prodlist, dict(cat=name + '|' + sub_name ))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul[@id="products-list"]/li/a')
    for prod in prods:
        name = prod.xpath(".//span[@class='hidden-desktop']//text()").string(multiple=True)
        url = prod.xpath("@href").string()

        revs = prod.xpath(".//svg[not(@name='stars-0')]")
        if revs:
            session.queue(Request(url), process_product, dict(context, url=url, name=name))
        else:
            return

    next_url = data.xpath("//li[@class='next']/a//@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, context)


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.category = context["cat"]
    product.url = context["url"]
    product.ssid = product.url.split("/")[-1].split('.html')[0]
    product.manufacturer = data.xpath("//a[@class='h1 brand-name']//text()").string(multiple=True)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data,context, session):
    product = context['product']

    revs = data.xpath('//li[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = context["url"]
        review.title = rev.xpath('.//div[@class="meta-data"]//strong/text()').string()
        review.date = rev.xpath('following::meta[1][@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        author_id = rev.xpath('.//a[@data-customer]/@data-customer').string()
        if author and author_id:
            author_url = 'https://www.consobaby.co.uk/flexiall/ajax/customer?id=' + author_id
            review.authors.append(Person(name=author, ssid=author_id, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('following::ul[li[@class="pros"]][1]/li[@class="pros"]//text()').string(multiple=True)
        if pros and pros.replace("Strengths:", "").strip().lower() not in XPROSCONS:
            pros = pros.replace("Strengths:", "").strip()
            review.add_property(type="pros", value=pros)

        cons = rev.xpath('following::ul[li[@class="cons"]][1]/li[@class="cons"]//text()').string(multiple=True)
        if cons and cons.replace("Weaknesses:", "").strip().lower() not in XPROSCONS:
            cons = cons.replace("Weaknesses:", "").strip()
            review.add_property(type="cons", value=cons)

        grade = rev.xpath('following::meta[@itemprop="ratingValue"][1]/@content').string()
        if grade:
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))

        grades = rev.xpath("following::ul[@class='details'][1]/li")
        for grade in grades:
            name = grade.xpath(".//span[@class='label']//text()").string()
            value = grade.xpath(".//span[@class='value']/svg//@name").string().split("stars-")[-1]
            review.grades.append(Grade(name=name, value=float(value), best=5.0))

        excerpt = rev.xpath('following::div[@class="reviewBody"][1]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('•', '')
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = rev.xpath('.//span[@data-id]/@data-id').string()
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath("//a[@rel='next']//@href").string()
    if next_url:
        session.queue(Request(next_url), process_reviews, dict(context, product=product))

    elif product.reviews:
        session.emit(product)
