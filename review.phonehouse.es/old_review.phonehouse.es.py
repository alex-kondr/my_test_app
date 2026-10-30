from agent import *
from models.products import *


XCAT = ['Lo más top del verano: Samsung', 'Reacondicionados', 'reNuevos', 'Renting móviles', 'Compramos tu móvil', 'Asegura tu móvil','Tarifas móvil y fibra', 'Luz y gas natural', 'Promociones y ofertas', 'Servicios Phone House', 'Ayuda y contacto', 'Reparamos tu móvil', 'Ocio y Tiempo libre']
XCAT2 = ['todo en', 'ofertas', 'renting', 'reacondicionados', 'ver todos', 'top ', 'ventas', 'novedades', 'marcas']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.phonehouse.es/'), process_frontpage, {})



def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@class="menu-principal"]/li')
    for cat in cats:
        url = cat.xpath('a/@href').string()
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[strong[@class="titu-submenus"]]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('strong/text()').string()
                if cat1_name == name:
                    cat1_name = ''

                subcats = cat1.xpath('ul/li/a')
                if len(subcats) > 1 and not any(word in cat1_name.lower() for word in XCAT2):
                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('text()').string()
                        if not any(word in subcat_name.lower() for word in XCAT2):
                            session.queue(Request(url), process_cat_id, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_cat_id(data: Response, context: dict[str, str], session: Session):
    cat_id = data.xpath('//input/@data-item_list_id').string()
    if cat_id:
        prods_url = "https://www.phonehouse.es/busqueda/productsSearch.ajax?id=listado&estilosFinales=true&searcherId=" + cat_id + "&numPorPagina=1000&begin=0&end=1000&page=1&url"
        session.queue(Request(prods_url), process_prodlist, dict(context))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//li[@class="item-listado-final"]')
    for prod in prods:
        url = prod.xpath('a/@href').string()
        name = prod.xpath('.//h3/text()').string()
        ssid = prod.xpath('input/@data-item_id').string()
        brand = prod.xpath('input/@data-item_brand').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid, brand=brand))

    # no next page

def process_product(data: Response, context: dict[str, str], session: Session):
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