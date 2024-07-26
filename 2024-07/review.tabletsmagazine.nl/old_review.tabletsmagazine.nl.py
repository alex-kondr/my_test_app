from agent import *
from models.products import *

debug = True

def process_revlist(data, context, session):
   for rev in data.xpath("//h2/a"):
      url = rev.xpath("@href").string()
      title = rev.xpath(" descendant::text()").string(multiple=True)
      if url and title:
         name = re_search_once('Review: (.*)$', title)
         if name:
            session.queue(Request(url), process_review, dict(context, url=url, name=name, title=title))

   next = data.xpath("//a[@class='nextpostslink']/@href").string()
   if next:
      session.queue(Request(next), process_revlist, dict(context))

def process_review(data, context, session):
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.ssid = product.name
   product.category = 'Tablets'

   content = data.xpath("//div[@class='content-area post']").first()
   if content:
      review = Review()
      review.type = 'pro'
      review.title = context['title']
      review.url = context['url']
      review.ssid = re_search_once('postid-(\d+)', data.xpath("//body[regexp:test(@class,'postid-\d+')]/@class").string())
      if review.ssid:
         product.ssid = review.ssid
      else:
         review.ssid = review.title
      product.reviews.append(review)
 
      review.date = content.xpath("descendant::span[@class='meta-date']/text()").string(multiple=True)
      author = content.xpath("descendant::span[@class='meta-author']//a").first()
      if author:
         name = author.xpath("descendant::text()").string()
         url = author.xpath("@href").string()
         if url and name:
            review.authors.append(Person(name=name, ssid=name, profile_url=url))

      excerpt = content.xpath("div[@class='content']/p[following-sibling::node()[regexp:test(name(),'^h\d')][regexp:test(normalize-space(.),'Conclusie')]]//text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("div[@class='content']/p[normalize-space(text())]//text()").string(multiple=True)
      if excerpt:
         review.add_property(type='excerpt', value=excerpt)

      for pro in content.xpath(" descendant::div[@class='rating-positive']//ul/li"):
         line = pro.xpath("descendant::text()").string()
         if line:
            review.add_property(type='pros', value=line)

      for con in content.xpath(" descendant::div[@class='rating-negative']//ul/li"):
         line = con.xpath("descendant::text()").string()
         if line:
            review.add_property(type='cons', value=line)

      conclusion = content.xpath("div[@class='content']/p[preceding-sibling::node()[regexp:test(name(),'^h\d')][regexp:test(normalize-space(.),'Conclusie')]]//text()").string(multiple=True)
      if conclusion:
         review.add_property(type='conclusion', value=conclusion)

      value = content.xpath("descendant::span[@class='value']/text()").string()
      if value:
         review.grades.append(Grade(name='Rating', type='overall', value=float(value), best=10.0))

   if product.reviews:
      session.emit(product)

def run(context, session):
   session.browser.agent = "Mozilla/6.0"
   session.queue(Request('http://www.tabletsmagazine.nl/category/tablet-reviews/'), process_revlist, dict())
