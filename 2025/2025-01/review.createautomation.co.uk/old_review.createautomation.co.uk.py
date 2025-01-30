from agent import *
from models.products import *


def process_frontpage(data, context, session):
    for cat in data.xpath("//div[@id='modCategory']/ul[@class='mobile']/li/a[@class='cat']"):
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_subcategory, dict(url=url, cat=name))
    

def process_subcategory(data, context, session):
    subcats = data.xpath("//div[@class='sub-categories-format']/ul[@class='columns-3']/li/div[@class='sub-categories']/a")
    for subcat in subcats:
        name = context['cat'] + "|" + subcat.xpath("span//text()").string()
        url = subcat.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_subcategory, dict(context, url=url, cat=name))
    
    if not subcats:
        process_products(data, context, session)


def process_products(data, context, session):
    prods = data.xpath("//div[@id='itemsBlock']/div[@class='productBlockContainer vat_enabled columns-3']/div/div[@class='product-item item-template-0 alternative']")
    for prod in prods:
        name = prod.xpath("div[@class='name']//text()").string(multiple=True)
        url = prod.xpath("div[@class='name']/a//@href").string() 
        rating = prod.xpath("div[@class='stars']/span//text()").string()
        if rating != '(0)':
            session.queue(Request(url, use='curl'), process_review, dict(context, url=url, name=name))

    next = data.xpath("//div[@id='itemsBlock']/div[@class='paging'][2]/a[contains(., 'Next')]//@href").string()
    if next:
        session.queue(Request(next, use='curl'), process_products, context)


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat'] 
    product.url = context['url']
    product.ssid = context['url'].split("/")[-1].split(".html")[0]

    sku_id = data.xpath("//div[@class='product-id']/span[@id='product_id']//text()").string()
    if sku_id == 'SON-':
        sku_id = data.xpath("//input[contains(@name,'OptID_')]/@value").string()
    if sku_id:
        product.sku = sku_id

    revs = data.xpath("//div[@class='reviewsBlock']/div[@class='user_reviews']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath("div[@class='review-info']/div[@itemprop='name']//text()").string()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath("div[@class='review-info']/em[@class='reviewed-by']//text()").string(multiple=True).split("on ")[-1]
        
        author_name = rev.xpath("div[@class='review-info']/em[@class='reviewed-by']/span[@itemprop='author']//text()").string(multiple=True)
        review.authors.append(Person(name=author_name, ssid=author_name))
        review.ssid = product.ssid + '-' + review.date + '-' + author_name

        excerpt = rev.xpath("div[@class='review-info']/div[@itemprop='description']//text()").string(multiple=True)        
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        
        grade_overall = rev.xpath("div[@class='star-rating']//@alt").string()
        if grade_overall:
            grade_overall = int(grade_overall.split(" Stars")[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5))
        
        if excerpt:
            product.reviews.append(review)

    session.emit(product)


def run(context, session):
    session.queue(Request("https://www.createautomation.co.uk", use='curl'), process_frontpage, dict())
    