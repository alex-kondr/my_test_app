from agent import *
from models.products import *
import re

from Ft.Xml import ReaderException

debug = True

def run(context, session):
   session.browser.agent = "Mozilla/6.0"
   session.queue(Request("http://www.greenskeeper.org/productreviews/reviews.cfm"), process_productlist, {})

def process_productlist(data, context, session):
   try:
      posts = data.xpath("/")
   except ReaderException:
      return

   for prod in data.xpath("//div[@class='title']/descendant::a[1]"):
      name = prod.xpath("descendant::text()").string(multiple=True)
      url = prod.xpath("@href").string()
      if url and name:
         session.queue(Request(url), process_review, dict(context, url=url, name=name))

   next = data.xpath("//div[@class='nextprev']//a[regexp:test(normalize-space(.),'next')]/@href").string()
   if next:
      session.queue(Request(next), process_productlist, dict(context))

def process_review(data, context, session):
   try:
      posts = data.xpath("/")
   except ReaderException:
      return

   product = Product()
   product.name = context['name']
   product.category = data.xpath("//td[@class='pathnavagation']/descendant::a[position()>1]/text()").join('|')
   product.url = context['url']
   product.ssid = product.name

   process_userreviews(data, {'product':product, 'url':context['url']}, session)

   session.emit(product)

def process_userreviews(data, context, session):
   product = context['product']
   num = context.get('num', 0)

   print len(data.xpath("//div[@id='listreviewsratingtable']"))
   for rev in data.xpath("//div[@id='listreviewsratingtable']"):
      num += 1
      title = rev.xpath("following::td[1]/div[@class='title']//text()").string(multiple=True)
      date = rev.xpath("following::td[1]/div[@class='date']//text()").string(multiple=True)
      summary = rev.xpath("following::td[1]/div[@class='review']//text()").string(multiple=True)

      ureview = Review()
      ureview.type = 'user'
      ureview.title = title
      ureview.url = context['url']

      ureview.date = date
      author = rev.xpath("preceding-sibling::div[@class='name']/a").first()
      if author:
         name = author.xpath("descendant::text()").string(multiple=True)
         url = author.xpath("@href").string(multiple=True)
         if name and url:
            ssid =get_url_parameter(url, 'regid')
            ureview.authors.append(Person(name=name, ssid=ssid, profile_url=url))
      else:
         name = rev.xpath("preceding-sibling::div[@class='name']/text()").string(multiple=True)
         if name:
            ureview.authors.append(Person(name=name, ssid=name))
      ureview.ssid = '%s-%s-%s'%(product.ssid, name, date)

      if summary:
         product.reviews.append(ureview)
         ureview.properties.append(ReviewProperty(type='summary', value=summary))

      for rating in rev.xpath("descendant::td[@class='labels']"):
         score = len(rating.xpath("following-sibling::td//img[regexp:test(@src,'starfull.gif')]"))
         title = rating.xpath("descendant::text() ").string(multiple=True)
         if title and score:
            if title == 'Overall':
               ureview.grades.append(Grade(name=title, type='overall', value=score, best=5))
            else:
               ureview.grades.append(Grade(name=title, value=score, best=5))

   next = data.xpath("/descendant::th[descendant::a][1]/p/text()[regexp:test(self::text(),'\d+')]/following-sibling::a[1]/@href").string()
   if next:
      session.queue(Request(next), process_userreviews, {'product':product, 'url':next, 'num':num})

 