from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.megagadgets.nl', force_charset='utf-8', use='curl'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(a/span/text(), "Categorieën")]/div/div/div[h3]')
    for cat in cats:
        name = cat.xpath('h3//text()').string(multiple=True)

        subcats = cat.xpath('.//a')
        for subcat in subcats:
            subcat_name = subcat.xpath('text()').string()
            url = subcat.xpath('@href').string()
            session.queue(Request(url+'?product_list_limit=108&product_list_order=reviews_count', force_charset='utf-8', use='curl'), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "product-card__details")]')
    for prod in prods:
        name = prod.xpath('a[contains(@class, "product-card__name")]/text()').string()
        url = prod.xpath('a[contains(@class, "product-card__name")]/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "review-count")]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, force_charset='utf-8', use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(., '"@type":"Product"')]//text()''').string())
    except:
        return

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.sku = data.xpath('//div[contains(div//text(), "SKU")]/div[contains(@class, "value")]//text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(div//text(), "Merk")]/div[contains(@class, "value")]//text()').string()

    ean = data.xpath('//div[contains(div//text(), "EAN")]/div[contains(@class, "value")]//text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type="id.ean", value=ean)

    revs = prod_json.get('review', [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get('datePublished')
        if date:
            review.date = date.split()[0]

        author = rev.get('author', {}).get('name')
        if author:
            email = rev.get('name')
            if email and "@" in email:
                review.authors.append(Person(name=author, ssid=author, email=email))
            else:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            grade_overall = float(grade_overall / 20)
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        excerpt = rev.get('description')
        if excerpt:
            excerpt = excerpt.split("---")[0].replace('\r\n', ' ').replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # loaded all reviews
