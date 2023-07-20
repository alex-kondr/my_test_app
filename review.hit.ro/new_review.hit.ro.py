from agent import *
from models.products import *


XCAT = ['Stiri', 'Diverse']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.hit.ro/'), process_frontpage, dict())
    

def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="mdl-layout__header-row"]/a[@class="mdl-navigation__link"][text()]')
    for cat in cats:
        name = cat.xpath('text()').string()
        
        if name not in XCAT:
            subcats = cat.xpath('following-sibling::div[1]//li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_category, dict(cat=name+'|'+subcat_name))
                

def process_category(data, context, session):
    prods = data.xpath('//div[@class="mdl-card__title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))
        
    next_url = data.xpath('//a[i[text()="skip_next"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))
        
        
def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('--')[-1].replace('.html', '')
    
    review = Review()
    review.url = product.url
    review.type = 'pro'
    
    date = data.xpath('//span[@class="mdl-chip__text"]/text()').string()
    if date:
        date = date.split(',')[0]
        review.date = date
    
    title = data.xpath('//head/title/text()').string()
    if title:
        review.title = title
        
    excerpt = data.xpath('//div[br]/text()|//p[br]//text()|//div[br]/b/text()|//div[br]/strong/text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
        
        review.ssid = review.digest(excerpt)
        
        product.reviews.append(review)
        
        session.emit(product)
