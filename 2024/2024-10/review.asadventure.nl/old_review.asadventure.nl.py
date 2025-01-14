from agent import *
from models.products import *
import simplejson


CAT = ["Fietsen", "Reizen", "Kamperen"]
SUBCAT = ["Nieuwe collectie", "Verhuur", "Ecocheque producten", "Professioneel", "Promoties", "Veilig in het verkeer"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.asadventure.com/', use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='as-o-main-nav']//li[contains(@class,'as-a-menu-item--menu-bar')]")
    for cat in cats:
        name_1 = cat.xpath(".//a/text()").string()
        if name_1 in CAT:
            subcats = cat.xpath(".//a[contains(@data-qa, '2_level_item')]")
            for subcat in subcats:
                name_2 = subcat.xpath("text()").string()
                if name_2 not in SUBCAT:
                    url = subcat.xpath("@href").string()
                    session.queue(Request(url, use="curl"), process_prodlist, dict(cat=name_1+"|"+name_2))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='as-t-product-grid__item']")
    for prod in prods:
        name = prod.xpath(".//span[contains(@class, 'as-m-product-tile__name')]/text()").string()
        url = prod.xpath(".//a/@href").string()
        brand = prod.xpath(".//span[contains(@class, 'as-m-product-tile__brand')]//text()").string(multiple=True)
        revs_count = prod.xpath(".//span[contains(@class, 'as-a-text as-a-text--subtle as-a-text--xs')]/text()").string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url, use="curl"), process_product, dict(context, name=name, url=url, brand=brand, revs_count=revs_count))

    next_page = data.xpath("//a[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, use="curl"), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.manufacturer = context['brand']
    product.category = context['cat']

    info = data.xpath("//script[@type='text/javascript'][starts-with(text(), 'var productInfo = ')]//text()").string()
    if info:
        info = simplejson.loads(info.split(' = ')[-1])
        product.ssid = info["productCode"]
        product.sku = info["productCode"]
        ssid = info["productId"]
        url = "https://www.asadventure.com/api/aem/review/product/" + ssid + "?shopId=95&market=be&mainWebshop=asadventure&language=nl&anaLang=nl&ignoreLang=true&size=" + context['revs_count']
        session.do(Request(url, use="curl"), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']
    data = data.content.replace("{}\r\n", "")
    if not data:
        return
    revs = simplejson.loads(data)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['reviewId']
        review.date = str(rev['dateInserted']).split('T')[0]

        author_name = rev.get('customerName')
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('reviewTextPositive')
        if pros:
            for pro in pros.splitlines():
                if pro:
                    pro = pro.strip()
                    review.add_property(type='pros', value=pro)

        cons = rev.get('reviewTextNegative')
        if cons:
            for con in cons.splitlines():
                if con:
                    con = con.strip()
                    review.add_property(type='cons', value=con)

        excerpt = rev['reviewTitle']
        if excerpt:
            excerpt = excerpt.strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)
                product.reviews.append(review)
                
    if product.reviews:
        session.emit(product)
