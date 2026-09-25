from agent import *
from models.products import *

debug = True

def process_revlist(data: Response, context: dict[str, str], session: Session):
   for rev in data.xpath("//div[@class='post_header_title']/h5/a"):
      url = rev.xpath("@href").string()
      title = rev.xpath("descendant::text()").string(multiple=True)
      if url and title:
         session.queue(Request(url), process_review, dict(url=url, title=title))

   nexturl = data.xpath("//div[@class='pagination']/p/a[@class='prev_button']/@href").string()
   if nexturl:
      session.queue(Request(nexturl), process_revlist, dict())

def process_review(data: Response, context: dict[str, str], session: Session):
   product = Product()
   product.name = context['title']
   product.url = context['url']
   product.ssid = product.name
   product.category = data.xpath("//a[@rel='category tag' and not(regexp:test(@href,'reviews'))]/text()").join('|')
   if not(product.category):
      product.category = 'Golf Equipment'

   content = data.xpath("//div[regexp:test(@id,'post-\d+')]").first()
   if content:
      review = Review()
      review.type = 'pro'
      review.title = context['title']
      review.url = context['url']
      review.ssid = re_search_once('(\d+)', content.xpath("@id").string())
      if review.ssid:
         product.ssid = review.ssid
      product.reviews.append(review)

      review.date = data.xpath("//span[@class='post_info_date']//text()").string(multiple=True)

      summary = content.xpath("p/strong[regexp:test(text(),'Description')]/following-sibling::node()/descendant-or-self::text()").string(multiple=True)
      if not(summary):
         summary = content.xpath("descendant::strong[regexp:test(text(),'Description')]/following-sibling::node()/descendant-or-self::text()").string(multiple=True)
      if not(summary):
         summary = content.xpath("p[normalize-space(text())][following-sibling::node()[regexp:test(normalize-space(.),'Impressions')]]/descendant-or-self::text()").string(multiple=True)
      if not(summary):
         summary = content.xpath("p[normalize-space(text())]/descendant-or-self::text()").string(multiple=True)
      if summary:
         review.properties.append(ReviewProperty(type='summary', value=summary))

      excerpt = content.xpath("p/strong[regexp:test(text(),'Review')]/following-sibling::node()/descendant-or-self::text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("descendant::strong[regexp:test(text(),'Review')]/following-sibling::node()/descendant-or-self::text()").string(multiple=True)
      if not(excerpt):
         excerpt = content.xpath("p[normalize-space(text())][preceding-sibling::node()[regexp:test(normalize-space(.),'Impressions')]]/descendant-or-self::text()").string(multiple=True)
      if not(excerpt):
         excerpt = data.xpath("//div[@class='post_header single']/p//text()").string(multiple=True)
      if excerpt:
         excerpt = excerpt.split('Follow us on ')[0]
         review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

   if product.reviews:
      session.emit(product)

def run(context: dict[str, str], session: Session):
   session.browser.agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:19.0) Gecko/20100101 Firefox/19.0'
   session.queue(Request('http://www.equip2golf.com/category/reviews/'), process_revlist, {})