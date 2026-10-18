from agent import *
from models.products import *

debug = True

def process_revlist(data: Response, context: dict[str, str], session: Session):
    category = context['category']
    for list in data.xpath("//div[@class='gridnext-grid-post-inside']"):
        url = list.xpath("(.)/div[2]/h3/a/@href").string()
        name = list.xpath("(.)/div[2]/h3/a//text()[string-length(normalize-space(.))>1]").join("")
        date = list.xpath("(.)/div[3]/div[1]/span[2]//text()[string-length(normalize-space(.))>1]").string()
        avt_u = list.xpath("(.)/div[3]/div[1]/span[1]/a/@href").string()
        avt_n = list.xpath("(.)/div[3]/div[1]/span[1]/a//text()[string-length(normalize-space(.))>1]").string()
        exc = list.xpath("(.)/div[4]//text()[string-length(normalize-space(.))>1]").string()
        if url and name:
           session.queue(Request(url), process_review, {'url' : url, 'name' : name, 'date' : date, 'avt_u' : avt_u, 'avt_n' : avt_n, 'exc' : exc, 'category' : category})

    nexturl = data.xpath("//div[@class='nav-links']/a[@class='next page-numbers']/@href").string()
    if nexturl :
       session.queue(Request(nexturl), process_revlist, dict(context))

def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url']
    product.category = context['category']

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = context['url']
    review.ssid = product.ssid
    product.reviews.append(review)

    review.date = context['date']

    avt_n = context['avt_n']
    avt_u = context['avt_u']
    if avt_n and avt_u:
       review.authors.append(Person(name = avt_n, profile_url = avt_u, ssid = review.ssid)) 
  
    for list in data.xpath("//div[@class='entry-content gridnext-clearfix']//img"):
        src = list.xpath("@src").string()
        if src:
           product.properties.append(ProductProperty(type="image" , value = {'src': src}))

    excerpt = data.xpath("//div[@class='entry-content gridnext-clearfix']/p[text()[string-length(normalize-space(.))>100] or *//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>100]").join("")
    if excerpt:  
       review.properties.append(ReviewProperty(type="excerpt", value = excerpt))

    con = data.xpath("//div[@class='entry-content gridnext-clearfix']/p[text()[string-length(normalize-space(.))>100] or *//text()[string-length(normalize-space(.))>100]][last()]//text()[string-length(normalize-space(.))>100]").join("")
    if con:  
       review.properties.append(ReviewProperty(type="conclusion", value = con))

    if excerpt :
       session.emit(product)

def run(context: dict[str, str], session: Session):
    session.queue(Request('http://gamechronicles.com/category/game-reviews/'), process_revlist, dict(category='Video Games', cat='game-reviews'))