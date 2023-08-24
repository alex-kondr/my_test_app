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

def getlastpar(txtlist):
   txtlist = [o.strip() for o in txtlist]
   print txtlist
   endindex = -1
   for idx in range(len(txtlist) - 1, -1, -1):
      line = txtlist[idx]
      if re_search_once("([!?.])$", line):
         endindex = idx
         break
   startindex = -1
   if endindex != -1:
      for idx in range(endindex - 1, -1, -1):
         line = txtlist[idx]
         if re_search_once("([^A-Z][!?.])$", line):
            startindex = idx
            print '*** %d'%len(' '.join(txtlist[startindex+1:endindex+1]))
            if len(' '.join(txtlist[startindex+1:endindex+1])) > 100:
               break
      if startindex != -1:
         lastpar = ' '.join(txtlist[startindex+1:endindex+1])
         lastpar = re.compile("\s+").sub(' ', lastpar)
         return lastpar.strip()

   return ''

def process_frontpage(data, context, session):
   for cat in data.xpath("//li[regexp:test(normalize-space(.),'^Tests')]//ul/li/a"):
      url = cat.xpath("@href").string()
      category = cat.xpath("descendant::text()").string(multiple=True)
      if url and not(category in ['Bestenlisten', 'mehr']):
         session.queue(Request(url), process_revlist, dict(category=category))

def process_revlist(data, context, session):
   for rev in data.xpath("//h3/a"):
      url = rev.xpath("@href").string()
      if url:
         if "testbericht/alle" in url:
            continue
         session.queue(Request(url), process_review, dict(context, url=url))

   nexturl = data.xpath("//div[@id='pagination_anchor']//span[regexp:test(text(),'^\d+$')]/following-sibling::a[1][regexp:test(normalize-space(.),'^\d+$')]/@href").string()
   if nexturl:
      session.queue(Request(nexturl), process_revlist, dict(context))

def process_review(data, context, session):
   review = Review()
   review.url = context['url']
   review.type = 'pro'
   product = Product()

   review.title = data.xpath("//h1[@class='content__headline']//text()").string(multiple=True)
   review.ssid = review.url.split("/")[-1].replace(".html", "")
   review.date = data.xpath("//span[@class='content__date']//text()").string(multiple=True)

   author = data.xpath("//span[@class='content__author'][2]/span").first()
   if author:
      name = author.xpath(".//text()").string(multiple=True)
      url = author.xpath("@href").string()
      if url and name:
         ssid = url.split("/")[-1].replace(".html", "")
         review.authors.append(Person(name=name, ssid=ssid, profile_url=url))
      elif name:
         ssid = name.replace(" ", "").lower()
         review.authors.append(Person(name=name, ssid=ssid))

   product.name = review.title.split(" im ")[0]
   product.ssid = review.ssid
   product.category = data.xpath("//span[@class='content__kicker']//text()").string(multiple=True)

   produrl = data.xpath("//div[@class='col-xs-46 col-xs-push-1 inline_amazon']/a[@class='inline_amazon__link']/@href")
   if not produrl:
      produrl = context['url']
   product.url = produrl

   summary = data.xpath("//p[@class='content__lead']//text()").string(multiple=True)
   if summary:
      review.properties.append(ReviewProperty(type='summary', value=summary))

   rate = len(data.xpath("//span[@class='glyphicon glyphicon-star inline_plusminuslist__rating--silverstar']"))
   if rate:
      review.grades.append(Grade(type='overall', name='Punkte', value=int(rate), best=5))

   excerpt = data.xpath("//node()[not(regexp:test(name(),'(h2|div|style|ul|strong)'))][normalize-space(text()|self::text())][following-sibling::h2[regexp:test(text(),'Fazit')]]/descendant-or-self::text()").string(multiple=True)
   if not(excerpt):
      excerpt = data.xpath("//node()[not(regexp:test(name(),'(h2|div|style|ul|strong)'))][normalize-space(text()|self::text())][following-sibling::node()[regexp:test(normalize-space(.),'Fazit')]]/descendant-or-self::text()").string(multiple=True)
   if not(excerpt):
      excerpt = data.xpath("//node()[not(regexp:test(name(),'(h2|div|style|ul|strong)'))][normalize-space(text()|self::text())]/descendant-or-self::text()").string(multiple=True)
   if excerpt:
      review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

   conclusion = data.xpath("//node()[not(regexp:test(name(),'(h2|div|style|ul|strong)'))][normalize-space(text()|self::text())][preceding-sibling::h2[regexp:test(text(),'Fazit')]]/descendant-or-self::text()").string(multiple=True)
   if conclusion:
      review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

   pros = data.xpath("//div[@class='inline_plusminuslist__section col-xs-24'][1]/ul/li")
   for pro in pros:
      line = pro.xpath(".//text()").string(multiple=True)
      review.properties.append(ReviewProperty(type='pros', value=line))

   cons = data.xpath("//div[@class='inline_plusminuslist__section col-xs-24'][2]/ul/li")
   for con in cons:
      line = con.xpath("text()").string(multiple=True)
      review.properties.append(ReviewProperty(type='cons', value=line))

   try:
      product.reviews.append(review)
      session.emit(product)
   except:
      print("Exception.")

def run(context, session):
   session.queue(Request('http://www.colorfoto.de/'), process_frontpage, {})