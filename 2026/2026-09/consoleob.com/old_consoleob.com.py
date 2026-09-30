from agent import *
from models.products import *

debug = True

import re

def getexcerpt(txtlist):
   excerpt = ''
   txtlist = [o.strip() for o in txtlist]
   for line in txtlist:
      excerpt += ' ' + line
      if re_search_once("([!?.])$", line) and len(line) > 100:
         break

   excerpt = re.compile("\s+").sub(' ', excerpt)

   return excerpt.strip()

def process_frontpage(data: Response, context: dict[str, str], session: Session):
   for cat in data.xpath("//ul[@id='subnav']/li[position()>2]/ul/li/a"):
      url = cat.xpath("@href").string()
      category = cat.xpath("descendant::text()").string(multiple=True)
      if url and category not in ['Features', 'Novels', 'Films']:
         session.queue(Request(url), process_revlist, dict(category=category))

def process_revlist(data: Response, context: dict[str, str], session: Session):
   for rev in data.xpath("//div[@class='front-post']//b//a"):
      url = rev.xpath("@href").string()
      title = rev.xpath("descendant::text()").string(multiple=True)
      if url and title:
         name = re_search_once("^(.*) Review$", title)
         if not(name):
            name = title
         session.queue(Request(url), process_review, dict(context, url=url, title=title, name=name))

   nexturl = data.xpath("//text()[regexp:test(normalize-space(self::text()), '^Next Page »$')]/preceding::a[1]/@href").string()
   if nexturl:
      session.queue(Request(nexturl), process_revlist, dict(context))

def process_review(data: Response, context: dict[str, str], session: Session):
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.ssid = product.name

   content = data.xpath("//div[@class='postarea']").first()
   if content:
      product.category = content.xpath(" div[@class='date']//a[regexp:test(@href,'category\/reviews') and not(regexp:test(@href,'\/reviews\/$'))]/text()").join('|')
      if not(product.category):
         product.category = context['category']

      review = Review()
      review.type = 'pro'
      review.title = context['title']
      review.url = context['url']
      review.ssid = review.title
      product.reviews.append(review)

      review.date = content.xpath(" div[@class='date']//span[@class='time']/text()").string(multiple=True)
      author = content.xpath("div[@class='date']//a[regexp:test(@href,'author')]").first()
      if author:
         name = author.xpath("descendant::text()").string(multiple=True)
         url = author.xpath("@href").string()
         if name and url:
            review.authors.append(Person(name=name, profile_url=url, ssid=name))

      excerpt = content.xpath("p[normalize-space(text()) and not(regexp:test(normalize-space(.),'^(Publisher|Developer)'))]//text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("p[normalize-space(span/text()) and not(regexp:test(normalize-space(.),'^(Publisher|Developer)'))]//text()").string(multiple=True)
      if excerpt:
         review.add_property(type='excerpt', value=excerpt)

      ratetxt = content.xpath("p[regexp:test(normalize-space(), '^\d+/10$')]//text()").string(multiple=True)
      if ratetxt:
         rate = re_search_once("(\d+\.?\d?)", ratetxt)
         if rate:
            review.grades.append(Grade(type='overall', name='Rating', value=float(rate), best=10.0))

   if product.reviews:
      session.emit(product)

def run(context: dict[str, str], session: Session):
   session.queue(Request('http://www.consoleob.com/'), process_frontpage, {})