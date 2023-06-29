import simplejson

from agent import *
from models.products import *


XCAT = ['Collections', 'Brands', 'Be Kind']
XSUBCAT = ['Shop by Colour', 'Shop by Brand', 'Gifts']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())
    
    
def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='site-header__nav__285 site-header__nav__menu no-bullet']/li[contains(@class, 'drop-down')]")
    for cat in cats:
        name = cat.xpath("a//text()").string()
        
        if name not in XCAT:
        
            cats1 = cat.xpath('.//ul[contains(@class, "drop-down__menu__")]')
            for cat1 in cats1:
                name1 = cat1.xpath('li[@class="drop-down__title"]/span//text()').string()
                name1 = name1 if name1 else ''
                
                if name1 not in XSUBCAT:
            
                    subcats = cat1.xpath(".//a[@class='top_level_link']")
                    for subcat in subcats:
                        subcat_name = subcat.xpath("span//text()").string()                        
                        url = subcat.xpath("@href").string()
                        session.queue(Request(url), process_category, dict(cat=name+"|"+name1+"|"+subcat_name))
            
            
def process_category(data, context, session):
    prods = data.xpath("//div[@class='product__details__title product__details__title--branded']/a")
    for prod in prods:
        name = prod.xpath("@title").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))    
    
    nex_page = data.xpath('//link[@rel="next"]/@href').string()
    
    if nex_page:
        session.queue(Request(nex_page), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    
    ssid = product.url.split('-')[-1]
    product.ssid = ssid
    
    revs_ssid = ssid.replace('p', 'pr')
    
    prod_json = simplejson.loads(data.xpath('//script[@type="application/ld+json"]//text()').string())
    
    rev_count = prod_json[0].get('aggregateRating', {}).get('reviewCount', 0)
    if rev_count > 0:
    
        manufacturer = prod_json[0].get('Brand', {}).get('name') 
        if manufacturer:
            product.manufacturer = manufacturer
                
        gtin13 = prod_json[0].get('gtin13')    
        if gtin13:
            product.add_property(type='id.ean', value=gtin13)
            
        sku = prod_json[0].get('SKU')    
        if sku:
            product.sku = sku
        
        revs_url = product.url.replace(ssid, revs_ssid)
        session.queue(Request(revs_url), process_reviews, dict(product=product, revs_ssid=revs_ssid, revs_url=revs_url))
             
        
def process_reviews(data, context, session):
    product = context['product']
    revs = data.xpath('//div[@class="product-reviews__ratings"]')
    
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = context['revs_url']
        review.ssid = context['revs_ssid']
        
        review.title = rev.xpath('div[@class="product-reviews__star"]/span[@class="product-reviews__subtitle"]//text()').string()
        
        review.date = rev.xpath('.//meta/@content').string()
        
        is_recommended = rev.xpath('.//span[contains(text(), "Would you recommend this product?")]/following-sibling::text()[1]').string()
        if is_recommended and ('no' not in is_recommended.lower()):
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))
        elif is_recommended and ('no' in is_recommended.lower()):
            review.properties.append(ReviewProperty(value=False, type='is_recommended'))
    
        author = rev.xpath('.//div[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))
            
        verified = rev.xpath('.//div[@class="product-review__verified"]//text()').string()
        if verified:
            review.add_property(type='is_verified_buyer', value=True)
            
        grade_overall = rev.xpath('count(.//i[@class="ico icon-star"])')
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
                
        grades = rev.xpath('span[@class="product-reviews__subtitle"]')
        
        for grade in grades:
            grade_name = grade.xpath('text()').string()
            
            grade = grade.xpath('following-sibling::text()[1]').string().replace('-', '').strip()
            try:
                if 0 < float(grade) <= 5:
                    review.grades.append(Grade(name=grade_name, value=float(grade), best=5.0))
            except ValueError:
                break
        
        excerpt = rev.xpath('p[@itemprop="reviewBody"]//text()').string()        
        
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            product.reviews.append(review)
            
    next_revs_url = data.xpath('//div[@class="cms-page--reviews__pagination"]//a[@title="next"]/@href').string()
    if next_revs_url:
        session.queue(Request(next_revs_url), process_reviews, dict(context, product=product, revs_url=next_revs_url))
         
    elif product.reviews:
        session.emit(product)
    