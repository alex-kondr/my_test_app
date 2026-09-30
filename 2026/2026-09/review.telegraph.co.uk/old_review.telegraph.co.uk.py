from agent import *
from models.products import *
import re

debug = True

def run(context: dict[str, str], session: Session):
   session.browser.agent = "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)"
   session.sessionbreakers = [SessionBreak(max_requests=10000)]
   session.queue(Request('http://www.telegraph.co.uk/archive/',), process_year, {})
 
def process_year(data: Response, context: dict[str, str], session: Session):
   for cat in data.xpath("//div[@class='summary']/h3/a[regexp:test(@href,'archive')]"):
      url = cat.xpath("@href").string()
      year = cat.xpath("descendant::text()").string(multiple=True)
      if url and year:
         session.do(Request(url), process_month, context)

def process_month(data: Response, context: dict[str, str], session: Session):
   for cat in data.xpath("//div[@class='summary']/h3/a[regexp:test(@href,'archive')]"):
      url = cat.xpath("@href").string()
      month = cat.xpath("descendant::text()").string(multiple=True)
      if url and month:
         session.do(Request(url), process_day, context)

def process_day(data: Response, context: dict[str, str], session: Session):
   for cat in data.xpath("//div[@class='summary']/h3/a[regexp:test(@href,'archive')]"):
      url = cat.xpath("@href").string()
      date = cat.xpath("descendant::text()").string(multiple=True)
      if url:
         session.do(Request(url), process_revlist, dict(date=date, url=url))

def process_revlist(data: Response, context: dict[str, str], session: Session):
   for rev in data.xpath("//h3/a[regexp:test(@href,'video-games.*review\.html')]"):
      newcontext = dict(context)
      name = rev.xpath("descendant::text()").string(multiple=True)
      url = rev.xpath("@href").string()
      if url:
         if re.search('preview', url):
            context['ispreview'] = True
         session.do(Request(url), process_review, dict(context, url=url, name=name))

def process_review(data: Response, context: dict[str, str], session: Session):
   product = Product()
   product.name = context['name']
   product.category = 'Games'
   product.url = context['url']
   product.ssid = re_search_once('\/(\d+)\/', product.url)

   review = Review()
   product.reviews.append(review)
   review.title = context['name']
   review.type = 'pro'
   review.url = context['url']
   review.ssid = product.ssid
   review.date = context['date']

   if context.get('ispreview', None):
      review.is_preview = True

   content = data.xpath("//div[@class='story']").first()
   if content:
      publisher = content.xpath("descendant::strong[regexp:test(text(),'Publisher')]").first()
      if not(publisher):
         publisher = content.xpath("following::body/descendant::strong[regexp:test(text(),'Publisher')]").first()
      if publisher:
         product.manufacturer = re_search_once(':\s(.*)$', publisher.xpath("descendant::text()").string(multiple=True))
         if not(product.manufacturer):
            product.manufacturer = publisher.xpath("following-sibling::text()[1]").string(multiple=True)

      format = content.xpath("descendant::strong[regexp:test(text(),'Format')] ").first()
      if not(format):
         format = content.xpath("following::body/descendant::strong[regexp:test(text(),'Format')] ").first()
      if format:
         product.category = re_search_once(':\s(.*)$', format.xpath("descendant::text()").string(multiple=True))
         if not(product.category):
            product.category = format.xpath("following-sibling::text()[1]").string(multiple=True)

      author = content.xpath("div[@class='byline']//a[regexp:test(@href,'journalists')]").first()
      if author:
         name = author.xpath("descendant::text()").string()
         url = author.xpath("@href").string()
         if name and url:
            review.authors.append(Person(name=name, ssid=name, profile_url=url))
      else:
         author = re_search_once('By\s(.*)\sPublished', content.xpath("div[@class='byline']/p[1]//text()").string(multiple=True))
         if author:
            review.authors.append(Person(name=author, ssid=author))

      score = data.xpath("//span[@itemprop='ratingValue']/text()").string()
      if score:
         review.grades.append(Grade(name='Rating', type='overall', best=5.0, value=float(score)))

      summary = data.xpath("//h2/text()").string(multiple=True)
      if summary:
         review.properties.append(ReviewProperty(type='summary', value=summary))

      excerpt = content.xpath("descendant::div[@class='body']/p[string-length(normalize-space(text()))>50]//text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("following::body/descendant::div[@class='body']/p[string-length(normalize-space(text()))>50]//text()").string(multiple=True)
      if excerpt:
         review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

      conclusion = content.xpath("descendant::div[@class='body']/p[string-length(normalize-space(text()))>50][last()]//text()").string(multiple=True)
      if not(conclusion):
         conclusion = data.xpath("following::body/descendant::div[@class='body']/p[string-length(normalize-space(text()))>50][last()]//text()").string(multiple=True)
      if conclusion:
         review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

      session.emit(product)


 