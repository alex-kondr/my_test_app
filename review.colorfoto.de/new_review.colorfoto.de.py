import simplejson

from agent import *
from models.products import *


XCAT = ['News']

url = 'https://www.connect-living.de/testbericht/shokz-openfit-test-3205394.html'

def run(context, session):
    session.queue(Request(url), process_product, dict(url=url, name='text_name', cat='test_cat'))
    # session.queue(Request('http://www.colorfoto.de/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="footersitemap__category"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        
        if name not in XCAT:
         subcats = cat.xpath('.//li/a')
         for subcat in subcats:
               subname = subcat.xpath('text()').string()
               url = subcat.xpath('@href').string()
               session.queue(Request(url), process_prodlist, dict(cat=name+"|"+subname))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="teaser__headline"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
      
        if 'Archiv' not in name:
            url = prod.xpath('@href').string()
            session.queue(Request(url), process_product, dict(context, url=url, name=name))
        
        
def process_product(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        if isinstance(prod_json, list):
            prod_json = prod_json[1]
        else:
            return
    else:
        return
   
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = context['url'].split('-')[-1].replace('.html', '')
    
    review = Review()
    review.type = "pro"
    review.url = product.url
    review.date = prod_json.get('datePublished').split()[0]
    
    authors = prod_json.get('author', {})
    if isinstance(authors, list):
        for author in authors:
            author = author.get('name')
            if author:
                review.authors.append(Person(name=author, ssid=author))
    elif authors:
        author = authors.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))
        
    summary = prod_json.get('description')
    if summary:
        review.add_property(type='summary', value=summary)
        
        
    pros = data.xpath('//li[span[@class="fas fa-plus-circle"]]')
    if pros:
        for pro in pros:
            pro = pro.xpath('text()').string()
            review.properties.append(ReviewProperty(type='pros', value=pro))
    
    cons = data.xpath('//li[span[@class="fas fa-minus-circle"]]')
    if cons:
        for con in cons:
            con = con.xpath('text()').string()
            review.properties.append(ReviewProperty(type='cons', value=con))
            
    conclusion = data.xpath('')
    
    excerpt = data.xpath('//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::p/text()|//div[@class="maincol__contentwrapper"]//h2[contains(text(), "Fazit")]/preceding-sibling::h2/text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        review.ssid = product.ssid

        product.reviews.append(review)
        
    if product.reviews:
        session.emit(product)
