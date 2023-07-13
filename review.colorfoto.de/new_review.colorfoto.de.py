import simplejson

from agent import *
from models.products import *


XCAT = ['News']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.colorfoto.de/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="footersitemap__category"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        if name in XCAT:
           continue

        subcats = cat.xpath('.//li/a')
        for subcat in subcats:
            subname = subcat.xpath('text()').string()
            url = subcat.xpath('@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name+"|"+subname))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="teaser__headline"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        if 'Archiv' in name:
           continue
        
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))
        
        
def process_product(data, context, session):
   prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
   if prod_json:
      prod_json = simplejson.loads(prod_json)
      if isinstance(prod_json, list):
         prod_json = prod_json[1]
   else:
      return
   
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.category = context['cat']
   product.ssid = context['url'].split('/')[-1].replace('.html', '')
   product.sku = context['url'].split('-')[-1].replace('.html', '')
   
   review = Review()
   review.type = "pro"
   review.url = product.url
   review.date = prod_json.get('datePublished').split()[0]
   
   authors = prod_json.get('author', {})
   if isinstance(authors, list):
      for author in authors:
         author = author.get('name')
         if author:
            review.authors.append(Person(name=author, ssid=author))
   elif authors:
      author = authors.get('name')
      if author:
         review.authors.append(Person(name=author, ssid=author))
      
   summary = prod_json.get('description')
   if summary:
      review.add_property(type='summary', value=summary)
   
   excerpt = prod_json.get('articleBody')
   if excerpt:
      review.add_property(type='excerpt', value=excerpt)

      review.ssid = product.ssid

      product.reviews.append(review)
      
   if product.reviews:
      session.emit(product)
