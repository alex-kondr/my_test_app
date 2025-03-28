from agent import *
from models.products import *
import simplejson

        
        print('altsid=', prod.get('altsid'))
        print('id=', prod.get('id'))
        print('sid=', prod.get('sid'))
        print('parent_product=', prod.get('parent_product'))
        print('title=', prod.get('title'))
        print('url=', prod.get('url'))
        


debug = True


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.storedj.com.au/'), process_frontpage, {})


def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@class='category-items']/li//a"):
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_category, dict(url=url))
           

def process_category(data, context, session):
    category = data.xpath("//h1/text()").string()
    products = data.xpath("//div[@class='product']//div/a/@href")
    for product in products:
        url = product.string()
        session.queue(Request(product.string()), process_product, dict(category=category, url=url)) 
        

def process_product(data, context, session):
    product = Product()
    content = simplejson.loads(data.xpath("//script[@type='application/ld+json']/text()").string())
    try:
        product.name = content['name']
    except KeyError:
        return # No data about product

    product.description = content['description']
    product.category = context['category']
    product.url = context['url']
    product.ssid = content['sku']
    product.sku = content['sku']
    product.manufacturer = content['brand']

    api_key = "7qfADKhmajegupAzebRovRVAjxdpou0s&sku"
    reviews_url = "https://api.trustpilot.com/v1/product-reviews/business-units/5487e55500006400057c0ed1/reviews?apikey=" + api_key + "=" + content['sku'] + "&perPage=100"
    session.queue(Request(reviews_url), process_reviews, dict(product=product)) 
       
 
def process_reviews(data, context, session):
    product = context['product']
    reviews = simplejson.loads(data.content)
    reviews = reviews['productReviews']
    for rev in reviews:
        review = Review()
        review.type = "user"
        review.ssid = rev['id']
        review.date = rev['createdAt']
        review.url = product.url
        review.grades.append(Grade(type="overall", value=rev['stars'], best=5)) 
        review.properties.append(ReviewProperty(name="excerpt", type="excerpt", value=rev['content']))
        review.authors.append(Person(name=rev['consumer']['displayName'], ssid=rev['consumer']['id']))
        product.reviews.append(review)
    if product.reviews:
        session.emit(product)
