from agent import *
from models.products import *
import simplejson


url = 'https://www.nailpolishdirect.co.uk/silicone-nipple-covers-black-reusable-self-adhesive-pack-of-2-p41542'


def run(context, session):
    # session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())
    session.queue(Request(url), process_product, dict(name='test_name', url=url, cat='test_cat'))
    
    
def process_frontpage(data, context, session):
    cats1 = data.xpath("//ul[@class='site-header__nav__285 site-header__nav__menu no-bullet']/li[contains(@class, 'drop-down')]")
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        print('name1=', name1)
        cats2 = cat1.xpath(".//a[contains(@class, 'top_level_link')]")
        print('len_cats2=', len(cats2))        
        for cat2 in cats2:
            name2 = cat2.xpath("span//text()").string()
            print('name2=', name2)
            url = cat2.xpath("@href").string()
            print('url=', url)
            session.queue(Request(url), process_category, dict(cat=name1+"|"+name2))
            
            
def process_category(data, context, session):
    prods = data.xpath("//li[@class='col l-col-8 m-col-third s-col-16']\
        //div[@class='product__details__title product__details__title--branded']")
    for prod in prods:
        name = prod.xpath("a/@title").string()
        print('name_product=', name)
        url = prod.xpath("a/@href").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))    
    
    nex_page = data.xpath('//div[@class="col l-col-18 m-col-22 text-align-right s-text-align-center"]\
        //a[@class="next-page page-arrow page_num ico icon-right"]/@href').string()
    
    if nex_page:
        print('pages!!!!!!!!!!!')
        session.do(Request(nex_page), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    
    detail_product = data.xpath('//script[@type="application/ld+json"]//text()').string()
    detail_product = simplejson.loads(detail_product)[0]    
    # print('detail_product=', detail_product)
    print('detail_product_sku=', detail_product['SKU'])
    print('detail_product_gtin13=', detail_product['gtin13'])
    print('detail_product_Brand=', detail_product['Brand']['name'])
    
    product.manufacturer = detail_product['Brand']['name']
    product.add_property(type='id.ean', value=detail_product['gtin13'])
    product.sku = detail_product['SKU']
    
    context['product'] = product
    
    revs_url = data.xpath('//div[@class="product-reviews__review-summary_bottom"]\
        /span[@class="product-reviews__write-review"]\
        /a[contains(text(), "Read all")]/@href').string()
    print('revs_url=', revs_url)
    revs = data.xpath('//div[@class="flex flex--fw-wrap"]//div[contains(@class, "product-reviews__ratings")]')
    print('len_revs=', len(revs))
    
    if revs_url:
        session.do(Request(revs_url), process_reviews, dict(context, revs_url=revs_url))
        
    elif revs:
        for rev in revs:
            review = Review()
            review.type = "user"
            review.url = product.url
            review.date = rev.xpath('.//li[strong[contains(text(), "Review Date")]]/text()')\
                .string().replace('-', '').strip()
            print('review.date=', review.date)
      
            author = rev.xpath('.//div[@class="col l-col-32"]//div[@class="flex"]/div//text()').string()
            print('author=', author)
            if author:
                review.authors.append(Person(name=author, ssid=author))
                
            grade_overall = rev.xpath('.//li[@class="cf" and div[contains(text(), "Overall Rating")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            print('len(grade_overall)=', len(grade_overall))
            if len(grade_overall) > 0:
                review.grades.append(Grade(type='overall', name="Overall Rating", value=len(grade_overall), best=5.0))
                
            grade_quality = rev.xpath('.//li[@class="cf" and div[contains(text(), "Quality")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            print('len(grade_quality)=', len(grade_quality))
            if len(grade_quality) > 0:
                review.grades.append(Grade(name="Quality", value=len(grade_quality), best=5.0))
                
            grade_ease_of_assembly = rev.xpath('.//li[@class="cf" and div[contains(text(), "Ease of Assembly")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            print('len(grade_ease_of_assembly)=', len(grade_ease_of_assembly))
            if len(grade_ease_of_assembly) > 0:
                review.grades.append(Grade(name="Ease of Assembly", value=len(grade_ease_of_assembly), best=5.0))
            
            grade_delivery = rev.xpath('.//li[@class="cf" and div[contains(text(), "Delivery")]]\
                    //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            print('len(grade_delivery)=', len(grade_delivery))
            if len(grade_delivery) > 0:
                review.grades.append(Grade(name="Delivery", value=len(grade_delivery), best=5.0))
                
            grade_value_for_money = rev.xpath('.//li[@class="cf" and div[contains(text(), "Value for Money")]]\
                    //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
            print('len(grade_value_for_money)=', len(grade_value_for_money))
            if len(grade_value_for_money) > 0:
                review.grades.append(Grade(name="Value for Money", value=len(grade_value_for_money), best=5.0))
            
            excerpt = rev.xpath('.//div[@class="row"]/div[@class="col l-col-32"]/p//text()').string()
            print('excerpt=', excerpt)
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)
                review.ssid = excerpt
                product.reviews.append(review)
                
        if product.reviews:
            session.emit(product)
            
        
def process_reviews(data, context, session):
    product = context['product']
    revs = data.xpath('//div[@class="product-reviews__ratings"]')
    dates = data.xpath('//meta[@itemprop="datePublished"]')
    authors = data.xpath('//div[@itemprop="author"]//text()')
    
    for rev, date, author in zip(revs, dates, authors):
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = date.xpath('@content').string()
        print('review.date=', review.date)
    
        author = author.string()
        print('author=', author)
        if author:
            review.authors.append(Person(name=author, ssid=author))
            
        grade_overall = rev.xpath('div[@class="product-reviews__star"]\
            /i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        print('len(grade_overall)=', len(grade_overall))
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', name="Overall Rating", value=len(grade_overall), best=5.0))
            
        grade_quality = rev.xpath('.//li[@class="cf" and div[contains(text(), "Quality")]]\
            //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        print('len(grade_quality)=', len(grade_quality))
        if len(grade_quality) > 0:
            review.grades.append(Grade(name="Quality", value=len(grade_quality), best=5.0))
            
        grade_ease_of_assembly = rev.xpath('.//li[@class="cf" and div[contains(text(), "Ease of Assembly")]]\
            //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        print('len(grade_ease_of_assembly)=', len(grade_ease_of_assembly))
        if len(grade_ease_of_assembly) > 0:
            review.grades.append(Grade(name="Ease of Assembly", value=len(grade_ease_of_assembly), best=5.0))
        
        grade_delivery = rev.xpath('.//li[@class="cf" and div[contains(text(), "Delivery")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        print('len(grade_delivery)=', len(grade_delivery))
        if len(grade_delivery) > 0:
            review.grades.append(Grade(name="Delivery", value=len(grade_delivery), best=5.0))
            
        grade_value_for_money = rev.xpath('.//li[@class="cf" and div[contains(text(), "Value for Money")]]\
                //i[contains(@class, "ico icon-star") and not(contains(@class, "inactive"))]')
        print('len(grade_value_for_money)=', len(grade_value_for_money))
        if len(grade_value_for_money) > 0:
            review.grades.append(Grade(name="Value for Money", value=len(grade_value_for_money), best=5.0))
        
        excerpt = rev.xpath('.//div[@class="row"]/div[@class="col l-col-32"]/p//text()').string()
        print('excerpt=', excerpt)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            review.ssid = excerpt
            product.reviews.append(review)
            
    if product.reviews:
        session.emit(product)
    
    