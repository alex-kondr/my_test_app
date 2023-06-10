from agent import *
from models.products import *
import simplejson


def run(context, session):
    # session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())
    session.queue(Request('https://www.nailpolishdirect.co.uk/silicone-nipple-covers-black-reusable-self-adhesive-pack-of-2-p41542'), process_product, dict())
    
    
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
    # product.name = context['name']
    # product.url = context['url']
    # product.ssid = product.url.split('/')[-1]
    # product.category = context['cat']
    
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
        /span[@class="product-reviews__write-review"]/a/@href').string()
    revs = data.xpath('//div[@class="flex flex--fw-wrap"]//div[contains(@class, "product-reviews__ratings")]')
    
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
            if author:
                review.authors.append(Person(name=author, ssid=author))
                
            grade_overall = data.xpath('')
        
        
        
def process_reviews(data, context, session):
    product = context['product']
    revs = data.xpath('//div[@class="flex flex--fw-wrap"]')