import string
from agent import *
from models.products import *
import re

debug = True


def process_categorys(data, context, session):
    for view_categoryline in data.xpath("//ul[@class='nav-list']/li//a[text()[string-length(normalize-space(.))>1]]"): 
        url = view_categoryline.xpath("(.)/@href").string()
        name = view_categoryline.xpath("(.)//text()[string-length(normalize-space(.))>1]").join("")  
        if url and name:
           session.queue(Request(url, max_age = 0), process_category, {'cat': name })

def process_category(data, context, session):
    cat = context['cat']
    for view_categoryline1 in data.xpath("//div[@class='content']"): 
        url = view_categoryline1.xpath("(.)/ancestor::div[1]/span[1]//a/@href").string()
        name = view_categoryline1.xpath("(.)/h3[@class='article-name']//text()[string-length(normalize-space(.))>1]").join("")
        date = view_categoryline1.xpath("(.)/p[@class='byline']//time/@datetime").join("")        
        if url:
           session.queue(Request(url, max_age = 0), process_view_product, {'url': url, 'name': name, 'date' : date, 'category' : cat})

def process_view_product(data, context, session):
    product = Product()  
    product.name = context['name'] 
    product.url = context['url'] 
    product.ssid = context['url'] 
    product.category = 'Gear'
  
    review = Review()  
    review.product = product.name   
    review.url = product.url   
    review.ssid = product.ssid 
    review.type = "pro" 
    review.date = context['date']

    avt_n = data.xpath("//div[@class='author-byline__authors']//a//text()[string-length(normalize-space(.))>1]").join("")
    avt_u = data.xpath("//div[@class='author-byline__authors']//a/@href").join("")
    if avt_n and avt_u:
       review.authors.append(Person(name = avt_n, profile_url = avt_u, ssid = review.ssid)) 
 
  
    for list in data.xpath("//div[@id='article-body']/div[@class='image-full-width-wrapper']//img"):
        src = list.xpath("@src").string()
        if src:
           product.properties.append(ProductProperty(type="image" , value = {'src': src}))

    excerpt = data.xpath("//div[@id='article-body']/p[text()[string-length(normalize-space(.))>100] or *//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>100]").join("")
    if excerpt:  
       review.properties.append(ReviewProperty(type="excerpt", value = excerpt))

    con = data.xpath("//div[@id='article-body']/p[text()[string-length(normalize-space(.))>100] or *//text()[string-length(normalize-space(.))>100]][last()]//text()[string-length(normalize-space(.))>100]").join("")
    if con:  
       review.properties.append(ReviewProperty(type="conclusion", value = con))

    for lisp in data.xpath("//div[@class='box contrast less-space pro-con'][div[h4[@class='icon icon-plus_circle']]]//ul/li"):
        pros = lisp.xpath("(.)//text()[string-length(normalize-space(.))>1]").join("")
        if pros: 			
           review.properties.append(ReviewProperty(type="pros", value = pros))

    for lisc in data.xpath("//div[@class='box contrast less-space pro-con'][div[h4[@class='icon icon-minus_circle']]]//ul/li"):
        cons = lisc.xpath("(.)//text()[string-length(normalize-space(.))>100]").join("")
        if cons: 			
           review.properties.append(ReviewProperty(type="cons", value = cons))

    i = 0
    for listGrade in data.xpath("//span[@class='chunk rating']/span[@class='icon icon-star']"):
        val_grade = listGrade.xpath("(.)/@class").join("")   
        if val_grade:
            i = i + 1
    if i > 0:
       review.grades.append(Grade(type = 'overall', value = i, worst = 0,  best = 10)) 

    product.reviews.append(review)   
    session.emit(product)

def run(context, session):
    #i = 100
    #while i >= 20:
    #    i = i - 2
    #    url = 'https://www.musicradar.com/more/reviews/reviews/latest/'+'151'+str(i)+'66797'
    session.queue(Request('https://www.musicradar.com/', max_age = 0), process_categorys, {} )  