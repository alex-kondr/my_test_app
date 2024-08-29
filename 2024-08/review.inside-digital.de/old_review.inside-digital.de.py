from agent import *
from models.products import *

debug = True

import re

def process_frontpage(data, context, session):
   for cat in data.xpath("//div[@id='main_menu']//a[regexp:test(@href,'erfahrungsberichte')]"):
      category = cat.xpath("ancestor::ul[1]/preceding-sibling::a//text()").string(multiple=True)
      url = cat.xpath("@href").string()
      if url and category:
         session.queue(Request(url), process_productlist, dict(url=url, category=category))

def process_productlist(data, context, session):
   for opt in data.xpath("//select[@class='inputegal']/option[position() > 1]"):
      name = opt.xpath("descendant::text()").string(multiple=True)
      value = opt.xpath("@value").string()
      if name and value:
         fname = name.replace(' - ','_').replace(' ','-').replace('/','-').replace('+','')
         url = 'http://www.inside-digital.de/%s/%s/%s_datum_erfahrungsberichte_1.html'%(context['category'].lower(), fname.lower(), value)
         session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=value))

def process_product(data, context, session):
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.ssid = context['ssid']
   product.category = context['category']

   for cnt, url in enumerate(data.xpath("//h4/a[normalize-space(.)]/@href").strings()):
      session.do(Request(url), process_review, dict(product=product, url=url, count=cnt+1))

   if product.reviews:
      session.emit(product)

def process_review(data, context, session):
   product = context['product']
   count = context['count']

   content = data.xpath("//div[@id='erfahrungsbericht_view']").first()
   if content:
      review = Review()
      review.type = 'user'
      review.title = product.name
      review.url = context['url']
      review.ssid = '%s-%s'%(product.ssid, count)
      product.reviews.append(review)
   
      datetxt = content.xpath("p[regexp:test(text(),'Datum')]/text()").string(multiple=True)
      if datetxt:
         review.date = re_search_once("(\d+\.\d+\.\d+)", datetxt)
      authortxt = content.xpath("p[regexp:test(text(),'Autor')]/text()").string(multiple=True)
      if authortxt:
         author = re_search_once("^Autor: (.*)$", authortxt)
         if author:
            review.authors.append(Person(name=author, ssid=author))

      ratetxt = content.xpath("p[regexp:test(text(),'Bewertung')]/img/@alt").string()
      if ratetxt:
         rate = re_search_once("(\d+)/10", ratetxt)
         if rate:
            review.grades.append(Grade(name='Gesamteindruck', type='overall', value=float(rate), best=10.0))

      for g in content.xpath("table[@class='bewertungen']/tr/td[2]/img[@class='stars']"):
         name = g.xpath("preceding::td[1]//text()").string(multiple=True)
         ratetxt = g.xpath("@title").string()
         if name and ratetxt:
            rate = re_search_once("(\d+)/10", ratetxt)
            if rate:
               review.grades.append(Grade(name=name, value=float(rate), best=10.0))

      pro = content.xpath("p[regexp:test(text(),'^Pro')]/text()").string()
      if pro:
         line = re_search_once("^Pro: (.*)$", pro)
         if line:
            review.add_property(type='pros', value=line)

      con = content.xpath("p[regexp:test(text(),'^Contra')]/text()").string()
      if con:
         line = re_search_once("^Contra: (.*)$", con)
         if line:
            review.add_property(type='cons', value=line)

      conclusion = content.xpath(" div[@class='bericht_text']//text()").string(multiple=True)
      if conclusion:
         review.add_property(type='conclusion', value=conclusion)


def run(context, session):
   session.queue(Request('http://www.inside-digital.de/'), process_frontpage, dict())
