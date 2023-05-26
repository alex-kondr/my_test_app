from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.navishop.nl/index.php'), process_frontpage, {})
        

def process_frontpage(data, context, session):
    categs = data.xpath('//ul[@id="categories"]/li/a[not(regexp:test(text(),"Accessoires|Autospecifiek"))]')
	for cat in categs: 
		category = cat.xpath('./text()').string(multiple=True)
		url = cat.xpath('@href').string()
		session.queue(Request(url), process_cat, dict(context, url=url, category=category))

def process_cat(data, context, session):
	products = data.xpath('//div[@class="infoBoxContents"]//div[@class="small_product"]')
	if not products:
		categs = data.xpath('//td[contains(@style,"background: #ff9e00")]/a[b]')
		for cat in categs: 
			category = cat.xpath('./text()').string(multiple=True)
			url = cat.xpath('@href').string()        
			session.queue(Request(url), process_category, dict(context, url=url, category=category))
	else: 
		process_productlist(data, context, session)


def process_product(data, context, session):
	product = Product()
	product.name = context[“name”] 
	product.url = context[“url”] 
	product.category = context[“category”]
	product.ssid = product.url.split('-')[-1].replace('.html','')

	reviews = data.xpath('//a[contains(text(),"Lees alle reviews")]')
	if reviews:
		url = reviews.xpath('@href').string()
		session.do(Request(url), process_reviews, dict(context, url=url, product=product)
        )
	if product.reviews:
		session.emit(product)


def process_reviews(data, context, session):
	revs = data.xpath('//tr[td/table[@class="infoBox"]]')
	for rev in revs:
		review = Review()
		review.type = 'user'

        revUser = rev.xpath('preceding-sibling::tr[1]/descendant::td[@class="main"]/b/text()').string().split(' van ')[-1]
		review.authors.append(Person(name=revUser, ssid=review.ssid))

		review.date = rev.xpath('preceding-sibling::tr[1]/descendant::td[@class="smallText"]/text()').string().split(', ')[-1]
		review.url = context['url']
		review.ssid = get_url_parameter(review.url, "reviews_id") + revUser + review.date
        
        revText = rev.xpath('descendant::td[@class="main"]//text()').string(multiple=True)
		if revText:
			review.add_property(type='summary', value=revText)

		revGrade = rev.xpath('count(descendant::img[contains(@src,"layout/review-ster-on.jpg")])')
		if revGrade:
			review.grades.append(Grade(name='Customer Rating', value=revGrade, worst=0.0, best=5.0))

			context['product'].reviews.append(review)
   