from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://www.rollei.de/collections/"), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath("//a[@class='list-collections__item image-zoom has-overlay']")
    for cat in cats:
        cat_name = cat.xpath(".//following-sibling::div[@class='list-collections__item-info'][1]/h2/text()").string()
        cat_url = cat.xpath("@href").string()
        session.queue(Request(cat_url), process_category, dict(context, cat=cat_name))

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_frontpage, context)


def process_category(data, context, session):
    items = data.xpath("//a[@class='product-item-meta__title']")
    for item in items:
        item_url = item.xpath("@href").string()
        item_name = item.xpath(".//text()").string()
        session.queue(Request(item_url), process_product, dict(context, name=item_name, url=item_url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.sku = data.xpath("//span[@class='product-meta__sku-number']//text()").string()
    product.ssid = product.sku or context['url'].split('/')[-1]

    scripts = data.xpath("//script[contains(.,'gtin13')]//text()")
    if not scripts:
        scripts = data.xpath("//script[contains(@type,'application/ld+json')]//text()")

    for script in scripts:
        script = simplejson.loads(script.string())

        if script.get('@type') == "Product":
            brand = script.get('brand')
            if brand:
                brand = brand.get('name')
                if brand:
                    product.manufacturer = brand

            ean = script.get('gtin13')
            if ean:
                product.add_property(type='id.ean', value=ean)
                if ean:
                    break

    revs = data.xpath("//div[@class='jdgm-rev jdgm-divider-top']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath("//@data-review-id").string()
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']//text()").string(multiple=True)

        date = rev.xpath(".//span[@class='jdgm-rev__timestamp jdgm-spinner']//@data-content").string()
        if date:
            review.date = date.split(' ')[0]

        author = rev.xpath(".//span[@class='jdgm-rev__author']//text()").string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span[@class='jdgm-rev__rating']/@data-score").string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath(".//span[@itemprop='description']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            if not review.ssid:
                review.ssid = review.digest()

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
