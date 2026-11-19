#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *

def run(context: dict[str, str], session: Session):
   session.queue(Request('https://www.pcworld.com/reviews'), process_reviewlist, dict(context, max_retries=5))

def process_reviewlist(data: Response, context: dict[str, str], session: Session):
   cnt = 0
   for rev in data.xpath("//h3/a"):
      cnt += 1
      title = rev.xpath("descendant::text()").string()
      url = rev.xpath("@href").string()
      rated = re_search_once('(\d\.?\d?)', rev.xpath("following::div[@class='item-meta'][1]/div/@style").string())
      if url and title:
         fixurl = "/".join(url.split('/')[0:-1])
         session.queue(Request(fixurl), process_review, dict(context, url=fixurl, title=title))

   if cnt == 20:
      page = context.get('page', 1)
      options = """-H 'authority: www.pcworld.com' -H 'accept: */*' -H 'content-type: application/x-www-form-urlencoded; charset=UTF-8' -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36' -H 'x-requested-with: XMLHttpRequest' """
      options += """ --data-raw 'action=ajaxload&page={}&filters=%5B%7B%27label%27%3A%27Reviews%27%2C%27value%27%3A9%2C%27tax%27%3A%27story_types%27%7D%5D&perpage=20&offset=0&exclude=1&template=archive&viewport=desktop&editions=Array&languages=en&hub=b2c&_ajaxnonce=784a01a426' --compressed """.format(page)
      r = agent.Request('https://www.pcworld.com/wp-admin/admin-ajax.php', max_age=0, use='curl', curl_options='-s -L --insecure ' + options, force_charset='utf-8')
      session.queue(r, process_reviewlist, dict(context, page=page+1))

def process_review(data: Response, context: dict[str, str], session: Session):
   jstxt = data.xpath("//script[regexp:test(.,'\"Product\"')]/text()").string()
   if not(jstxt):
       return

   json = simplejson.loads(jstxt)
   cats = [d for d in json[0]['itemListElement'] if d['position']== 2]
         
   product = Product()
   product.name = json[1]['name']
   product.manufacturer = json[1]['review']['brand']['name']
   product.url = data.xpath("//link[@rel='canonical']/@href").string()
   product.ssid = re_search_once('article\/(\d+)', product.url)

   if cats:
      product.category = cats[0]['name']
   else:
      product.category = 'unknown'
 
   review = Review()
   review.type = 'pro'
   review.title = context['title']
   review.url = context['url']
   review.ssid = product.ssid + '-review'

   review.date = re_search_once('^(.*\d{4})', data.xpath("//span[@class='posted-on']/text()").string())
   author = data.xpath("//span[@class='author vcard']/a").first()
   if author:
      name = author.xpath("descendant::text()").string()
      url = author.xpath("@href").string()
      if url and name:
         review.authors.append(Person(name=name, ssid=name, profile_url=url))

   summary = data.xpath("//p[@class='verdict']//text()").string(multiple=True)
   if summary:
      review.properties.append(ReviewProperty(type='summary',value=summary))

   excerpt = data.xpath("//div[@class='subheadline']//text()").string(multiple=True)
   if excerpt:
      review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

   for pro in data.xpath("//ul[@class='pros review-list']/li"):
      line = pro.xpath("descendant::text()").string(multiple=True)
      if line:
         review.properties.append(ReviewProperty(type="pros", value=line))

   for con in data.xpath("//ul[@class='cons review-list']/li"):
      line = con.xpath("descendant::text()").string(multiple=True)
      if line:
         review.properties.append(ReviewProperty(type="cons", value=line))

   value = re_search_once('(\d\.?\d?)', data.xpath("//div[@class='starRating']/@style").string())
   if value:
      review.grades.append(Grade(name='Rating', type='overall', value=float(value), best=5.0))

   for award in data.xpath("//div[@class='review']//img"):
      src = award.xpath("@src").string()
      alt = award.xpath("@alt").string()
      if src and alt:
        review.properties.append(ReviewProperty(type='awards', value=dict(image_src=src, name=alt)))

   if summary or value:
      product.reviews.append(review)

   if product.reviews:
      session.emit(product)
