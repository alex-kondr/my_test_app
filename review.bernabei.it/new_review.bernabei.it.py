from agent import *
from models.products import *
import simplejson


XCAT = ['Tutti i vini', 'Altro', 'Magazine']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bernabei.it'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[contains(@class, "topmenu")]/ul/li[contains(@class, "main")]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "item")]/a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//ul[contains(@aria-label, "Submenu for")]/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div[contains(@class, "text")]/span/text()').string()

                subcats = cat1.xpath('.//ul/li//a')
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string()
                    url = subcat.xpath('@href').string()
                    
                    print name+'|'+cat1_name+'|'+subcat_name
                    # session.queue(Request(url), process_category, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "carousel-item")]')
    if not subcats:
        subcats = data.xpath('//dd[contains(@class, "tipologia")]/ol/li/a')
    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)

    for subcat in subcats:
        name = subcat.xpath('div[contains(@class, "text")]/text()').string() or subcat.xpath('text()').string().strip('( )')
        if name.lower() in context['cat'].lower():
            name = ''

        url = subcat.xpath('.//a/@href').string() or subcat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//ul[contains(@class, "products-grid")]//h3[@class="item-title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].rstrip('|')
    product.manufacturer = data.xpath('//div[contains(@class, "produttore")]/span/text()').string()
    product.ssid = data.xpath('//input[@name="product"]/@value').string()

    prod_json = data.xpath("""//script[contains(., '"@type": "Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        sku = prod_json.get('sku')
        if sku:
            product.sku = sku

    revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = 'https://www.bernabei.it/bernabei_customization/index/getreviewsprodotto?product_id={0}/'.format(product.ssid)
        session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="recensioni-container"]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('.//div[contains(@class, "titolo")]/text()').string()
        review.ssid = rev.xpath('.//div[@data-product]/@rel').string()
        review.date = rev.xpath('small[@class="date"]/text()').string()

        author = rev.xpath('.//div[contains(@class, "autore")]/span/text()').string()
        if author and author.strip():
            review.authors.append(Person(name=author, ssid=author))

        hlp_yes = rev.xpath('.//a[@class="voteup"]/span/text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//a[@class="votedown"]/span/text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev.xpath('.//div[@class="rating"]/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].rstrip(';%')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//div[contains(@class, "test")]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.rstrip(' +*.')
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs