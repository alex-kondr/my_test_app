from agent import *
from models.products import *

import simplejson


def run(context, session):
    session.queue(Request('https://star-mfg.com/products/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//li[contains(@class, 'product-category')]")
    category = context.get("cat")
    for cat in cats:
        name = cat.xpath("h2/text()").string()
        if category:
            name = category + '|' + name
        url = cat.xpath("a/@href").string()
        session.queue(Request(url), process_catlist, dict(cat=name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath("//ul[contains(@class, 'products')]/li")
    for prod in prods:
        name = prod.xpath("h2/text()").string()
        url = prod.xpath("a/@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = context["cat"]

    if '®' in product.name:
        product.manufacturer = product.name.split('®')[0].split()[-1]
    elif '™' in product.name:
        product.manufacturer = product.name.split('™')[0]
    elif product.name.startswith("Star ") or product.name.startswith("Star-Max "):
        product.manufacturer = product.name.split()[0]

    mpn = data.xpath("//span[@class='sku']/text()").string()
    if mpn and '*' in mpn:
        mpn = data.xpath("//div[contains(@class, 'woocommerce-product-gallery')]//img/@src").string()
        mpn = mpn.split('/')[-1].split('-')[0]
    if not mpn:
        product_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
        if product_json:
            product_info = simplejson.loads(product_json)
            mpn = product_info[2].get("mpn")
            if not mpn:
                mpn = product_info[2].get("sku")
    if mpn:
        product.properties.append(ProductProperty(type="id.manufacturer", value=mpn))
        product.sku = mpn

    imgs = data.xpath("//div[contains(@class, 'woocommerce-product-gallery')]//img/@src")
    for img in imgs:
        img = img.string()
        product.properties.append(ProductProperty(type='image', value=dict(src=img)))

    desc = data.xpath("(//div[@class='woocommerce-product-details__short-description']//p)[last()]/text()").string()
    info = data.xpath("(//div[contains(@aria-labelledby, 'tab-title-description')]/p|//div[contains(@aria-labelledby, 'tab-title-product_editor')]/p)//text()").string(multiple=True)
    if desc and info and desc not in info:
        desc += ' ' + info
    if desc:
        product.properties.append(ProductProperty(name='Description', value=desc))

    downloadable_urls = data.xpath("//div[contains(@aria-labelledby, 'tab-title-product_download')]/div").first()
    specs_url = downloadable_urls.xpath("div/div[descendant::h4[regexp:test(text(), 'spec', 'i')]]/following-sibling::div[1]//a/@href").string()
    if specs_url:
        product.properties.append(ProductProperty(type='link.manufacturer.spec', value=dict(url=specs_url, title='Specification')))

    guide_url = downloadable_urls.xpath("div/div[descendant::h4[regexp:test(text(), 'manual', 'i')]]/following-sibling::div[1]//a/@href").string()
    if guide_url:
        product.properties.append(ProductProperty(type='link.manufacturer.userguide', value=dict(url=guide_url, title='Brochure')))

    session.emit(product)
