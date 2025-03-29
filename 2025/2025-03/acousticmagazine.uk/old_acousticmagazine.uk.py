import string
from agent import *
from models.products import *
import re
import time

debug = True

def run(context, session): 
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.musicradar.com/reviews'), process_frontpage, {})
	
def process_frontpage(data, context, session):
    cnt = 0
    last_date = None
    for p in data.xpath("//div[@class[regexp:test(., 'listingResult')]][div[@class='content']]"):
        cnt += 1
        context['name'] = p.xpath(".//h3//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath(".//a/@href[regexp:test(., '\/reviews\/')]").string()
        last_date = p.xpath(".//time[@class[regexp:test(., 'published-date')]]/@data-published-date").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    if cnt == 10 and last_date:
        last_date = last_date.replace('Z', '')
        last_date = last_date.split('.')[0]
#        tstamp = time.mktime(time.strptime(last_date, '%Y-%m-%dT%H:%M:%S.%fZ'))
        tstamp = time.mktime(time.strptime(last_date, '%Y-%m-%dT%H:%M:%S'))
        tstamp = int(tstamp)
        
        url = "https://www.musicradar.com/more/reviews/reviews/latest/%d" % (tstamp)
        session.queue(Request(url), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace(' review', '')
    product.url = context['url']
    category = data.xpath("//a[@class='chunk']//text()[string-length(normalize-space(.))>0]").string()
    if not category:
        category = "Music Equipment"
    product.category = Category(name = category)
    product.ssid = data.xpath("//article[@class='review-article']/@data-id").string()

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//time[@itemprop='datePublished']/@datetime").string()
    excerpt = data.xpath("//body/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@class[regexp:test(., 'verdict')]]//p[.//text()[string-length(normalize-space(.))>0]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Verdict"))
    user_data = data.xpath("//span[@class[regexp:test(., 'by-author')]]/a[@href[regexp:test(., '\/author\/')]]").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    for pros in data.xpath("//div[@class[regexp:test(., 'pro-con')]]//h4[regexp:test(., 'Pros')]/following-sibling::ul[li][1]/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pros"))
    for cons in data.xpath("//div[@class[regexp:test(., 'pro-con')]]//h4[regexp:test(., 'Cons')]/following-sibling::ul[li][1]/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Cons"))
    grade = data.xpath("//meta[@itemprop='ratingValue']/@content").string()
    if grade:
        review.grades.append(Grade(name="Rating", value = grade, worst = 0, best = 5, type = 'overall'))

    product.reviews.append(review)
    session.emit(product)
