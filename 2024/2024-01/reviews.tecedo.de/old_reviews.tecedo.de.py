from agent import *
from models.products import *


X_CATS = ['Home', 'B-Ware ', 'Aktuelle Angebote']


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


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.tecedo.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath("//ul[@class='menu clearfix']/li")
    for cat in cats:
        name = cat.xpath("a//text()").string()
        if name not in X_CATS:
            cats2 = cat.xpath("div/div/ul/li")
            for cat2 in cats2:
                name2 = cat2.xpath("a//text()").string()
                if name2 not in X_CATS:
                    cat2_url = cat2.xpath("a/@href").string()
                    session.queue(Request(cat2_url), process_category, dict(cat=name + '|' + name2))


def process_category(data, context, session):
    strip_namespace(data)

    prods = data.xpath("//div[@class='item']")
    for prod in prods:
        name = prod.xpath("div[@class='item-meta-container']/span[@class='item-name']//text()").string()
        url = prod.xpath("div[@class='item-meta-container']/span[@class='item-name']/a/@href").string()

        revs_count = prod.xpath(".//div[@class='item-rating']/div/meta[@itemprop='reviewCount']/@content").string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//li[@class='next']/a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_category, context)


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath("//h1[@class='product-name']/span[@itemprop='brand']//text()").string()

    product.ssid = context['url'].split('/')[-1].replace('.html', '')
    product.sku = data.xpath("//ul[@class='product-list']/li/span[@itemprop]//text()").string()

    revs_url = 'https://api.ukw.cloud/app/backport/reviews/tec/de/' + product.sku + '?page=1'
    session.do(Request(revs_url), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context.get('product')

    revs = data.xpath("//ul/li")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath(".//h3/@title").string()

        aggregated = rev.xpath('.//p[contains(@title, "Ursprünglich erschienen auf")]')
        if aggregated:
            continue

        date = rev.xpath("(.//div[@class='truncate']/div/p)[2]//text()").string()
        if date:
            review.date = date.split(' ')[0]

        is_recommended = rev.xpath(".//p[contains(span, 'Empfiehlt dieses Produkt:')]/text()").string(multiple=True)
        if is_recommended == "Ja":
            review.add_property(type='is_recommended', value=True)
        elif is_recommended == "Nein":
            review.add_property(type='is_recommended', value=False)

        author = rev.xpath("(.//div[@class='truncate']/div/p)[1]//text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span[@class='i-star rating']")
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(len(grade_overall)), best=5.0))

        excerpt = rev.xpath(".//p[@class='overflow-ellipsis']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('[Diese Bewertung wurde im Rahmen einer Sonderaktion abgegeben.]', '').strip()
            excerpt = excerpt.replace('[Diese Bewertung wurde im Rahmen einer Werbeaktion eingeholt.]', '').strip()
            excerpt = excerpt.replace('[Anzeige][kostenlose Werbung][Produkttest]', '').strip()
            excerpt = excerpt.replace('[Diese Bewertung wurde nach Erhalt eines Anreizes (Gutschein, Rabatt, kostenlose Probe, Gewinnspiel, Wettbewerb mit Verlosung, etc.) eingereicht.]', '').strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)
                review.ssid = review.digest() if author else review.digest(excerpt)
                product.reviews.append(review)

    next_url = data.xpath("//a[span[@class='i-chevron-right']]/@href").string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))
