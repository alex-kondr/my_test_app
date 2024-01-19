from agent import *
from models.products import *


X_CATS = ['Home', 'B-Ware', 'Aktuelle Angebote']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.tecedo.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='menu clearfix']/li")
    for cat in cats:
        name = cat.xpath("a/text()").string()

        if name not in X_CATS:
            sub_cats = cat.xpath('.//ul[@class="mega-menu-list clearfix"]/li/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath("text()").string()
                url = sub_cat.xpath("@href").string()

                if sub_name not in X_CATS:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='item']")
    for prod in prods:
        name = prod.xpath("div[@class='item-meta-container']//a/text()").string()
        url = prod.xpath("div[@class='item-meta-container']//a/@href").string()

        revs = prod.xpath('.//div[@itemprop="aggregateRating"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//li[@class='next']/a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, context)


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].replace('.html', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('//tr[td[text()="Marke"]]/td[@class="body"]/text()').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()

    revs_url = 'https://api.ukw.cloud/app/backport/reviews/tec/de/' + product.sku
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[.//div[@class="flex-1 truncate"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath(".//h3/@title").string()

        date = rev.xpath('.//div[@class="flex mt-1 items-center space-x-2"]/p/text()').string()
        if date:
            review.date = date.split(' ')[0]

        author = rev.xpath('.//p[@class="text-gray-900 text-md font-medium truncate"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath("count(.//span[@class='i-star rating'])")
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_recommended = rev.xpath(".//p[contains(span, 'Empfiehlt dieses Produkt:')]/text()").string(multiple=True)
        if is_recommended == "Ja":
            review.add_property(type='is_recommended', value=True)
        elif is_recommended == "Nein":
            review.add_property(type='is_recommended', value=False)

        excerpt = rev.xpath(".//p[@class='overflow-ellipsis']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('[Diese Bewertung wurde im Rahmen einer Sonderaktion abgegeben.]', '').replace('[Diese Bewertung wurde im Rahmen einer Werbeaktion eingeholt.]', '').replace('[Anzeige][kostenlose Werbung][Produkttest]', '').replace('[Diese Bewertung wurde nach Erhalt eines Anreizes (Gutschein, Rabatt, kostenlose Probe, Gewinnspiel, Wettbewerb mit Verlosung, etc.) eingereicht.]', '').strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath("//a[span[@class='i-chevron-right']]/@href").string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
