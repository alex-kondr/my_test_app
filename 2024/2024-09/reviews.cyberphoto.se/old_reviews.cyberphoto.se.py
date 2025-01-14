from agent import *
from models.products import *


PROCESSED_REVS = [] # Will emit dupe reviews as they syndicate reviews over many similar products with or without lenses, different urls so we use "name" in the review itself as identifier/ Jonas


def process_category(data, context, session):
    for cat in data.xpath("//ul[@class='c-subnav__list']/li[@class='c-subnav__item']/a[@class='c-subnav__link']"):
        name = cat.xpath(".//text()").string(multiple=True).strip()
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_subcategory, dict(cat=name))


def process_subcategory(data, context, session):
    subcategory = data.xpath("//span[@class='hide-for-small']/following-sibling::ul[1][@class='c-subnav__list']//a")
    for subcat in subcategory:
        name = context['cat'] + "|" + subcat.xpath(".//text()").string(multiple=True).strip()
        url = subcat.xpath("@href").string()
        session.queue(Request(url), process_prodlist, dict(cat=name))

    if not subcategory:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath("//h3[@class='c-product-card__link-text']")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("preceding-sibling::a/@href").string()
        brand = prod.xpath("preceding-sibling::span[@itemprop='brand']//text()").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url, brand=brand))

    next = data.xpath("//li[@class='c-pagination__item next']/a/@href").string()
    if next:
        session.queue(Request(next), process_prodlist, context)


def process_product(data, context, session):    
    if not data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]"):
        return # If no excerpt

    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split("/")[-1]
    product.url = context['url']
    product.manufacturer = context['brand']
    product.category = 'Foto - Video'
    product.sku = data.xpath("//div[@class='c-product-sticky__brand']/span[2]//text()").string()

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    author = data.xpath("//p[contains(.,'Testad av')]//text()").string(multiple=True)
    if author:
        author = author.split("Testad av ")[-1].split(" ")[0]
        review.authors.append(Person(name=author, ssid=author))

    date = data.xpath("//p[contains(.,'Testad av')]//text()").string(multiple=True)
    if date:
        review.date = date.split("Testad av ")[-1].replace(author, '')
    
    summary = data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]//p[1]//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

        for processed_rev in PROCESSED_REVS:
            if summary in processed_rev:
                return

        PROCESSED_REVS.append(summary)
    
    conclusion = data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]//b[contains(., 'Slutsats')]/following-sibling::text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    pros = data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]//b[contains(., 'Plus')]/following-sibling::text()")
    for pro in pros:
        pro = pro.string().replace('+', '')
        review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]//b[contains(., 'Minus')]/following-sibling::text()")
    for con in cons:
        con = con.string().replace('-', '')
        review.add_property(type='cons', value=con)
    
    excerpt = data.xpath("//section[@aria-labelledby='product-test-heading']/following-sibling::div[@class='row'][1]//p[not(contains(., 'Plus'))][not(contains(., 'Minus'))][not(contains(., 'Slutsats'))]//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary,'')
        if conclusion:
            excerpt = excerpt.replace(conclusion,'')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if data.xpath("//img[contains(@src,'120x120guld_SE.png')]"):
        im_aw = data.xpath("//img[contains(@src,'120x120guld_SE.png')]/@src").string()
        product.properties.append(ProductProperty(type='awards', value={'name': 'Toppklass', 'image_src': im_aw}))
    
    if summary or conclusion or excerpt:
        product.reviews.append(review)
        session.emit(product)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cyberphoto.se/foto-video'), process_category, dict())
    