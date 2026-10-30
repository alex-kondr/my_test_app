from agent import *
from models.products import *


XCAT = ['Lo más top del verano: Samsung', 'Reacondicionados', 'reNuevos', 'Renting móviles', 'Compramos tu móvil', 'Asegura tu móvil','Tarifas móvil y fibra', 'Luz y gas natural', 'Promociones y ofertas', 'Servicios Phone House', 'Ayuda y contacto', 'Reparamos tu móvil', 'Ocio y Tiempo libre', 'Servicios']
XCAT2 = ['todo en', 'ofertas', 'renting', 'reacondicionados', 'ver todos', 'top ', 'ventas', 'novedades', 'marcas']


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
    
    # url = 'https://www.phonehouse.es/moviles-y-telefonia'
    # session.queue(Request(url), process_category, dict())
    session.queue(Request('https://www.phonehouse.es/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    
    text = data.xpath('//template[@data-field="extensions"]/parent::*//text()').string(multiple=True)
    print text

    # cats = data.xpath('//nav[contains(@class, "main-menu")]/ul/li//a')
    # for cat in cats:
    #     name = cat.xpath('.//text()').string(multiple=True)
    #     url = cat.xpath('@href').string()

    #     if name not in XCAT:
    #         session.queue(Request(url), procec_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@aria-roledescription="slide"]//a[@alt]').pretty()
    


def process_cat_id(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cat_id = data.xpath('//input/@data-item_list_id').string()
    if cat_id:
        prods_url = "https://www.phonehouse.es/busqueda/productsSearch.ajax?id=listado&estilosFinales=true&searcherId=" + cat_id + "&numPorPagina=1000&begin=0&end=1000&page=1&url"
        session.queue(Request(prods_url), process_prodlist, dict(context))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//li[@class="item-listado-final"]')
    for prod in prods:
        url = prod.xpath('a/@href').string()
        name = prod.xpath('.//h3/text()').string()
        ssid = prod.xpath('input/@data-item_id').string()
        brand = prod.xpath('input/@data-item_brand').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid, brand=brand))

    # no next page

def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.ssid = context['ssid']
    product.category = context['cat'].replace('||', '|')
    product.url = context['url']
    product.manufacturer = context['brand']

    revs = data.xpath('//li[@data-reviews-hiddens]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.ssid = rev.xpath('a/@id').string()
        review.date = rev.xpath('.//div[@class="fecha-start"]/span/text()').string()

        author = rev.xpath('.//div[@class="op-new-design"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[contains(@class, "valoracion")]/@class').string()
        if grade_overall:
            grade_overall = grade_overall.split('valoracion')[-1]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="mi-opinion"]/p/text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)