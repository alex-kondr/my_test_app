from agent import *
from models.products import *

debug = True

import re

def process_brand(data, context, session):
   for brand in data.xpath("//div[@class='inside-left-sidebar']//li[regexp:test(normalize-space(.),'^Camera Reviews')]/ul/li/a"):
      url = brand.xpath("@href").string()
      manufacturer = brand.xpath("descendant::text()").string(multiple=True)
      if url and manufacturer:
         session.queue(Request(url), process_revlist, dict(url=url, manufacturer=manufacturer, category='Cameras', page=1))

   for cat in data.xpath("//div[@class='inside-left-sidebar']//li[regexp:test(normalize-space(.),'^Camera Accessories')]/ul/li/a"):
      url = cat.xpath("@href").string()
      category = cat.xpath("descendant::text()").string(multiple=True)
      if url and category:
         session.queue(Request(url), process_revlist, dict(url=url, category=category, page=1))

def process_revlist(data, context, session):
   cnt = 0
   for rev in data.xpath("//h2[@class='entry-title']/a"):
      cnt += 1
      url = rev.xpath("@href").string()
      title = rev.xpath("descendant::text()").string(multiple=True)
      if url and title:
         name = re_search_once('^(.*) [Rr]eview', title)
         if name:
            session.queue(Request(url), process_review, dict(url=url, title=title, name=name))

   if cnt == 3:
      page = context.get('page', 1)
      nexturl = context['url'] + 'page/%s/'%(page+1)
      session.queue(Request(nexturl), process_revlist, dict(context, page=page+1))


def process_review(data, context, session):
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.ssid = product.name
   product.category = 'Cameras'

   content = data.xpath("//div[@class='inside-article']/div[@itemprop='text']").first()
   if content:
      review = Review()
      review.type = 'pro'
      review.title = context['title']
      review.url = context['url']
      review.ssid = re_search_once('(\d+)$', data.xpath("//article/@id").string())
      if review.ssid:
         product.ssid = review.ssid
      else:
         review.ssid = review.title
      product.reviews.append(review)

      summary = content.xpath("p[following-sibling::p[regexp:test(normalize-space(.),'Tags')]]/node()[regexp:test(normalize-space(.),':$')][1]/preceding-sibling::node()/descendant-or-self::text()").string(multiple=True)
      if not summary:
         summary = data.xpath("//div[@class='entry-content']/p[1]//text()").string(multiple=True)
      if summary:
         review.add_property(type='summary', value=summary)

      excerpt = content.xpath("p[following-sibling::h3]//text()").string(multiple=True)
      if excerpt:
         if summary:
             excerpt = excerpt.replace(summary, "")
         review.add_property(type='excerpt', value=excerpt)

   if product.reviews:
      session.emit(product)

def run(context, session):
   session.browser.agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:26.0) Gecko/20100101 Firefox/26.0"
   session.queue(Request('http://www.photoaxe.com/category/cameras/'), process_brand, {})