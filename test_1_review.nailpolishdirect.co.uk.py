import simplejson

from agent import *
from models.products import *


GRADE_NAMES = ['Quality', 'Ease of Assembly', 'Delivery', 'Value for Money']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())
    
    
def process_frontpage(data, context, session):
    cats1 = data.xpath("//ul[@class='site-header__nav__285 site-header__nav__menu no-bullet']/li[contains(@class, 'drop-down')]")
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        cats2 = cat1.xpath(".//a[contains(@class, 'top_level_link')]")
        for cat2 in cats2:
            name2 = cat2.xpath("span//text()").string()
            url = cat2.xpath("@href").string()
            session.queue(Request(url), process_category, dict(cat=name1+"|"+name2))
            
            
def process_category(data, context, session):
    prods = data.xpath("//li[@class='col l-col-8 m-col-third s-col-16']\
        //div[@class='product__details__title product__details__title--branded']")
    for prod in prods:
        name = prod.xpath("a/@title").string()
        url = prod.xpath("a/@href").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))    
    
    nex_page = data.xpath('//div[@class="col l-col-18 m-col-22 text-align-right s-text-align-center"]\
        //a[@class="next-page page-arrow page_num ico icon-right"]/@href').string()
    
    if nex_page:
        session.do(Request(nex_page), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']
    
    detail_product = data.xpath('//script[@type="application/ld+json"]//text()').string()
    detail_product = simplejson.loads(detail_product)[0]
    
    manufacturer = detail_product.get('Brand')    
    if manufacturer:
        manufacturer = manufacturer.get('name')
        if manufacturer:
            product.manufacturer = manufacturer
            
    gtin13 = detail_product.get('gtin13')    
    if gtin13:
        product.add_property(type='id.ean', value=gtin13)
        
    sku = detail_product.get('SKU')    
    if sku:
        product.sku = sku
    
    context['product'] = product
    
    revs_url = data.xpath('//div[@class="product-reviews__review-summary_bottom"]\
        /span[@class="product-reviews__write-review"]\
        /a[contains(text(), "Read all")]/@href').string()
    
    revs = data.xpath('//div[@class="flex flex--fw-wrap"]//div[contains(@class, "product-reviews__ratings")]')
    
    if revs_url:
        session.do(Request(revs_url), process_reviews, dict(context, revs_url=revs_url))
        
    elif revs:
        for rev in revs:
            review = Review()
            review.type = "user"
            review.url = product.url
            review.ssid = product.ssid
            
            is_recommended = rev.xpath('.//li[strong[contains(text(), "Would you recommend this product?")]]\
                /text()').string()
            if is_recommended and ('no' not in is_recommended.lower()):
                review.properties.append(ReviewProperty(value=True, type='is_recommended'))
            
            date = rev.xpath('.//li[strong[contains(text(), "Review Date")]]/text()').string()            
            if date:
                review.date = date.replace('-', '').strip()
      
            author = rev.xpath('.//div[@class="col l-col-32"]//div[@class="flex"]/div//text()')
            if len(author) == 1:
                author = author.string().strip()
                review.authors.append(Person(name=author, ssid=author))
            elif len(author) == 2:
                author = author[0].string().strip()
                review.authors.append(Person(name=author, ssid=author))
                review.add_property(type='is_verified_buyer', value=True)
                    
                
            grade_overall = rev.xpath('.//li[@class="cf" and div[contains(text(), "Overall Rating")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            if len(grade_overall) > 0:
                review.grades.append(Grade(type='overall', name="Overall Rating", value=float(len(grade_overall)), best=5.0))

            grades = rev.xpath('.//li[@class="cf"]')
        
            for grade in grades:
                grade_name = grade.xpath('div//text()').string()
                
                if grade_name in GRADE_NAMES:
                    grade = grade.xpath('.//i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
                    if len(grade) > 0:
                        review.grades.append(Grade(name=grade_name, value=float(len(grade)), best=5.0))
            
            excerpt = rev.xpath('.//div[@class="row"]/div[@class="col l-col-32"]/p//text()').string()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)
                product.reviews.append(review)
                
        if product.reviews:
            session.emit(product)
            
        
def process_reviews(data, context, session):
    product = context['product']
    revs = data.xpath('//div[@class="product-reviews__ratings"]')
    dates = data.xpath('//meta[@itemprop="datePublished"]')
    authors = data.xpath('//div[div[@itemprop="author"]]')
    
    for i, rev in enumerate(revs):
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = product.ssid
        review.date = dates[i].xpath('@content').string()
        
        is_recommended = rev.xpath('.//span[contains(text(), "Would you recommend this product?")]\
            /following-sibling::text()[1]').string()
        if is_recommended and ('no' not in is_recommended.lower()):
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))
    
        author = authors[i].xpath('div//text()')
        if len(author) == 1:
            author = author.string().strip()
            review.authors.append(Person(name=author, ssid=author))
        elif len(author) == 2:
            author = author[0].string().strip()
            review.authors.append(Person(name=author, ssid=author))
            review.add_property(type='is_verified_buyer', value=True)
            
        grade_overall = rev.xpath('div[@class="product-reviews__star"]\
            /i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', name="Overall Rating", value=float(len(grade_overall)), best=5.0))
                
        grades = rev.xpath('span[@class="product-reviews__subtitle"]')
        
        for grade in grades:
            grade_name = grade.xpath('text()').string()
            
            if grade_name in GRADE_NAMES:
                grade = grade.xpath('following-sibling::text()[1]').string().replace('-', '').strip()
                review.grades.append(Grade(name=grade_name, value=float(grade), best=5.0))          
        
        excerpt = rev.xpath('p[@itemprop="reviewBody"]//text()').string()
        summary = rev.xpath('div[@class="product-reviews__star"]/span[@class="product-reviews__subtitle"]//text()').string()
        
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            if summary:
                review.title = summary
            product.reviews.append(review)          
        elif summary:
            review.add_property(type='excerpt', value=summary)
            product.reviews.append(review)          
            
    next_revs_url = data.xpath('//div[@class="cms-page--reviews__pagination"]\
        //a[@class="next-page page-arrow page_num ico icon-right"]/@href').string()
    
    if next_revs_url:
        context['product'] = product
        session.do(Request(next_revs_url), process_reviews, dict(context, revs_url=next_revs_url))
         
    elif product.reviews:
        session.emit(product)
    