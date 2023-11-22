from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = "True"
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.kameraliike.fi"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath("//div[@id='products_megamenu']/div[contains(@class, 'griddi2')]/a[@data-id]")
    for cat1 in cats1:
        cat1_name = cat1.xpath("text()").string(multiple=True)
        cat1_id = cat1.xpath("@data-id").string()
        cats2 = data.xpath("//div[@id='products_megamenu']/div[@class='griddi']/div[@data-id='submenu_" + cat1_id + "']/div/div[contains(@class, 'title')]")
        for cat2 in cats2:
            cat2_name = cat2.xpath("a/text()").string()
            url = cat2.xpath("a/@href").string()
            cats3 = cat2.xpath("following-sibling::div/a")
            if not cats3:
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
            for cat3 in cats3:
                cat3_name = cat3.xpath("text()").string()
                url = cat3.xpath("@href").string()
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='product_container']")
    for prod in prods:
        name = prod.xpath(".//img[@title][1]//@title").string(multiple=True)
        url = prod.xpath(".//a//@href").string()
        rating = prod.xpath(".//div[@class='product_container_rating floatright']//span[@class='rating_size']//text()").string()
        if rating != '(0)':
            session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = context['name'].split(" ")[0]

    mpn = data.xpath("//span[@class='product_code_cont']/text()").string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)
    product.ssid = mpn or context['url'].split("/")[-1]

    revs = data.xpath("//div[@itemprop='review']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.date = rev.xpath("//meta[@itemprop='datePublished']/@content").string()

        author_name = rev.xpath("//span[@itemprop='author']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath("//span[@itemprop='ratingValue']/text()").string()
        if grade_overall:
            grade_overall = float(grade_overall.split('/')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath("div[contains(@class, 'review_text')]//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if author_name:
                review.ssid = review.digest()
            else:
                review.ssid = review.digest(excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
