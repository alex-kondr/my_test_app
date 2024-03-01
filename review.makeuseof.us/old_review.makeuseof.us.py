from agent import *
from models.products import *

debug = True

import re

def run(context, session):
   session.browser.agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0"
#   session.browser.use_new_parser = True
   session.sessionbreakers = [SessionBreak(max_requests=10000)]
   session.queue(Request('http://www.makeuseof.com/service/product-reviews/'), process_revlist, {})

def process_revlist(data, context, session):
   for rev in data.xpath("//div[@class='flexbox']/div[@class='item']"):
      url = rev.xpath("a/@href").string()
      title = rev.xpath(".//h4/text()[string-length(normalize-space(.))>0]").string(multiple=True)
      if url and title:
         name = re_search_once('^(.*) Review', title)
         if not(name):
            name = title
         if name:
            session.queue(Request(url), process_review, dict(context, url=url, title=title, name=name))

   next = data.xpath("//link[@rel='next']/@href").string()
   if next:
      session.queue(Request(next), process_revlist, dict(context))

def process_review(data, context, session):
   product = Product()

   content = data.xpath("//div[@class='single-post-container']/div").first()
   if content:
      product.name = data.xpath("//div[@class='single-post-recommendation']//span[@itemprop='name']/text()").string()
      if not(product.name):
         product.name = context['name']
      product.url = context['url']
      product.category = 'unknown'
      product.ssid = product.name

      review = Review()
      review.type = 'pro'
      review.title = context['title']
      review.url = product.url
      review.ssid = review.title
      product.reviews.append(review)

      review.date = content.xpath("following::body//span[@class='article-card-meta-date-short']/text()").string(multiple=True)
      author = content.xpath("following::body//span[@itemprop='author']/a").first()
      if author:
         url = author.xpath("@href").string()
         name = author.xpath("descendant::text()").string(multiple=True)
         if url and name:
            review.authors.append(Person(name=name, ssid=name, profile_url=url))

      summary = content.xpath("following::body//div[@class='single-post-recommendation']/span/text()[last()]").string(multiple=True)
      if summary:
         review.add_property(type='summary', value=summary)

      excerpt = content.xpath("following::body/p[following-sibling::div[@class='single-post-recommendation']][not(preceding-sibling::h2)]//text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("following::body/p[following-sibling::p[regexp:test(normalize-space(.),'The good')]]//text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("following::body//div[@itempro='reviewBody']/p[following-sibling::div[@class='single-post-recommendation']][not(preceding-sibling::h2)]//text()").string(multiple=True)
      if excerpt:
         review.add_property(type='excerpt', value=excerpt)

      conclusion = content.xpath("following::body/p[following-sibling::div[@class='single-post-recommendation']][preceding-sibling::h2[regexp:test(normalize-space(.),'The Verdict|Should you get|Should you buy','i')]]//text()").string(multiple=True)
      if not(conclusion):
         conclusion = content.xpath("following::body/p[following-sibling::div[@class='single-post-recommendation']][not(following-sibling::h2)]//text()").string(multiple=True)
      if not(conclusion):
         conclusion = content.xpath("following::body//div[@itempro='reviewBody']/p[following-sibling::div[@class='single-post-recommendation']][preceding-sibling::h2[regexp:test(normalize-space(.),'The Verdict|Should you get|Should you buy','i')]]//text()").string(multiple=True)
      if not(conclusion):
         conclusion = content.xpath("following::body//div[@itempro='reviewBody']/p[following-sibling::div[@class='single-post-recommendation']][not(following-sibling::h2)]//text()").string(multiple=True)
      if conclusion:
         review.add_property(type='conclusion', value=conclusion)

      for pro in content.xpath("following::body//p[regexp:test(normalize-space(.),'Advantages')]/following-sibling::ul[1]/li"):
         line = pro.xpath("descendant::text()").string(multiple=True)
         if line:
            review.add_property(type='pros', value=line)

      pros = content.xpath("following::body/p[regexp:test(normalize-space(.),'The good')]//text()[not(ancestor::strong)]").string(multiple=True)
      if pros:
         review.add_property(type='pros', value=pros)

      for con in content.xpath("following::body//p[regexp:test(normalize-space(.),'Disadvantages')]/following-sibling::ul[1]/li"):
         line = con.xpath("descendant::text()").string(multiple=True)
         if line:
            review.add_property(type='cons', value=line)

      cons = content.xpath("following::body/p[regexp:test(normalize-space(.),'The bad')]//text()[not(ancestor::strong)]").string(multiple=True)
      if cons:
         review.add_property(type='cons', value=cons)

      grade = content.xpath("following::body//span[@itemprop='ratingValue']/text()").string()
      if grade:
         review.grades.append(Grade(name='Rating', type='overall', value=float(grade), best=10.0))

      if review.properties and product.reviews:
         session.emit(product)
