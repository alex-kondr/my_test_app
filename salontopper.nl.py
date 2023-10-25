from agent import *
from models.products import *


# 234 -> 1900
# 4853 -> 6000
# 7123 -> 9000
# 9486 -> 10000


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.salontopper.nl/"), process_frontpage, dict())
    # session.queue(Request("https://www.salontopper.nl/product/sebastian-professional-volupt-spray-150ml-2033"), process_product, dict(cat='cat', name='name', url='https://www.salontopper.nl/product/sebastian-professional-volupt-spray-150ml-2033'))


# frontpage
# category
# product
# reviews
def process_frontpage(data, context, session):
    cats1 = data.xpath("//ul[@class='menu vertical drilldown']/li")
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        cats2 = cat1.xpath("ul/li")
        for cat2 in cats2:
            name2 = cat2.xpath("a//text()").string()
            cats3 = cat2.xpath("ul/li/a")
            for cat3 in cats3:
                name3 = cat3.xpath(".//text()").string()
                url = cat3.xpath("@href").string()
                session.queue(Request(url), process_category, dict(cat=name1+"|"+name2+"|"+name3))


def process_category(data, context, session):
    prods = data.xpath("//div[contains(@class,'product-gallery')]/div")
    for prod in prods:
        url = prod.xpath("a[@class='product-info']/@href").string()
        name = prod.xpath(".//div[@class='title']//text()").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath("//meta[@itemprop='brand']/@content").string()

    # SKU - product.sku    # без перевірки
    # EAN / GTIN - product.add_property(type='id.ean', value=ean)    # з перевіркою
    # MPN - product.add_property(type='id.manufacturer', value=mpn)    # з перевіркою

    ean = data.xpath("//strong[@itemprop='gtin13']//text()").string() # None
    if ean:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    revs_url = data.xpath("//a[contains(@href, '/product-reviews/')]/@href").string()
    if revs_url:
        session.do(Request(revs_url), process_reviews, dict(context, revs_url=revs_url))
    else:
        process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath("//div[@class='product-review']")
    for rev in revs:
        review = Review()
        review.type = "user" # pro / user
        review.url = context.get('revs_url', product.url)
        review.title = rev.xpath(".//div[@class='content']/span[@itemprop='name']//text()").string()
        review.date = rev.xpath(".//span[@itemprop='datePublished']/@content").string()

        # author

        author = rev.xpath(".//span[@itemprop='author']/span[@itemprop='name']//text()").string()
        if not author:
            author = rev.xpath(".//div[@class='author']/span[@itemprop='author']//text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author)) # profile_url

        # grade_overall
        grade_overall = rev.xpath(".//i[@class='fas fa-star']")
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=len(grade_overall), best=5.0))

        # grades

        # grades = rev.xpath()
        # for grade in grades:
        #     grade_name = grade.xpath().string()
        #     grade_val = grade.xpath().string()
        #     if grade_name and grade_val:
        #         review.grades.append(Grade(name=grade_name, value=float(grade_overall), best=5.0))

        # pros / cons

        # <p> 111 <span> 222 </span> 333 </p>
        # data.xpath("//p/text()").string() # 111
        # data.xpath("//p/text()").string(multiple=True) # 111 333
        # data.xpath("//p//text()").string(multiple=True) # 111 222 333

        # <p> <span> 111 </span> 222 </p>
        # data.xpath("//p//text()").string() # 111
        # data.xpath("//p//text()").string(multiple=True) # 111 222

        # pros = rev.xpath("")
        # for pro in pros:
        #     pro = pro.xpath(".//text()").string(multiple=True)
        #     if pro:
        #         review.add_property(type='pros', value=pro)

        # cons = rev.xpath("")
        # for con in cons:
        #     con = con.xpath(".//text()").string(multiple=True)
        #     if con:
        #         review.add_property(type='cons', value=con)

        # summary / conclusion / excerpt

        excerpt = rev.xpath(".//span[@itemprop='description']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath(".//span[@itemprop='description']/@id").string()
            if ssid:
                review.ssid = ssid.replace("fullReview-", "")
            else:
                review.ssid = review.digest()

            product.reviews.append(review)

    # next_page = data.xpath("").string()
    # if next_page:
    #     session.do(Request(next_page), process_reviews, context)
    # else:

    if product.reviews:
        session.emit(product)

# curl "https://prunesearch.com/manage?action=looksession&agent_id=20095" -k -u "georgesavr6@gmail.com:YUbhduJuids33" > log.txt
# curl "https://prunesearch.com/manage?action=yaml&agent_id=19734" -k -u "georgesavr6@gmail.com:YUbhduJuids33" > emit.yaml
