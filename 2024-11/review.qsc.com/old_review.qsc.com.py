from agent import *
from models.products import *
import hashlib


def run(context, session): 
    session.queue(Request('https://www.qsc.com/products/', use='curl'), process_catlist, {})
	

def process_catlist(data, context, session):
    cats1 = data.xpath("//div[@class='container container-full']")
    for cat1 in cats1:
        name1 = cat1.xpath("h3[@class='section-title']//text()").string()
        if name1:
            cats2 = cat1.xpath("div")
            for cat2 in cats2:
                name2 = cat2.xpath(".//h3//text()").string()
                if name2:
                    prods = cat2.xpath(".//div[@class='container-button-dropdown']/div//ul/li")
                    for prod in prods:
                        url = prod.xpath(".//a/@href").string()
                        name = prod.xpath(".//text()").string()
                        if url and name:
                            session.queue(Request(url, use='curl'), process_product, dict(context, url=url, name=name, cat=name1))

    # No next_page because all products are in this page


def process_product(data, context, session):
    revs_url = data.xpath("//a[contains(@href,'/review/')]/@href").string()
    if revs_url:
        session.do(Request(revs_url, use='curl'), process_reviews, dict(context))


def process_reviews(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = 'QCS'
    
    revs = data.xpath("//div[@class='qscreview']/div[@class='row']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//h4//text()").string()
        review.type = 'user'
        review.url = context['url']
        
        author_name = rev.xpath(".//h3//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        excerpt = rev.xpath(".//div[@class='ten-tablet']//p//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        
        grade = 0

        grade_star = rev.xpath(".//span[@class='product-ratings']/i[@class='onestar']")
        if grade_star:
            grade += len(grade_star)

        grade_half = rev.xpath(".//span[@class='product-ratings']/i[@class='halfstar']")
        if grade_half:
            grade += 0.5

        if grade > 0:
            review.grades.append(Grade(type='overall', value=grade, best=5.0))
        
        if author_name and excerpt:
            review.ssid = '%s-%s' % (product.ssid, hashlib.md5(author_name + excerpt).hexdigest())
            product.reviews.append(review)
    
    if product.reviews:
        session.emit(product)
