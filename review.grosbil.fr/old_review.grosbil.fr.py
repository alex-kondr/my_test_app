from agent import *
from models.products import *

debug = True

import re
XCAT = """http://www.grosbill.com/2-accessoires_telephonie-cat-mobilite_pda
http://www.grosbill.com/2-les_alarmes-cat-domotique_maison_numerique
"""
XCATNAME = ["CONSOMMABLES CONNECTIQUE"]
XCATS = ['Alarme', 'Accessoire Téléphonie']


def process_frontpage(data, context, session):
   for cat in data.xpath("//div[@id='navigation_wrapper']/ul/li/a"):
      category = cat.xpath("descendant::text()").string(multiple=True)
      url = cat.xpath("@href").string()
      if url not in XCAT and category not in XCATNAME:
         fixurl = url.split('#')[0]
         session.queue(Request(fixurl), process_category, dict(url=url, category=category))
 
def process_category(data, context, session):
   form = data.xpath("//form[@name='produit']").first()
   if form:
      catid = data.xpath("//input[@name='tdg']/@value").string()
      nexturl = 'https://www.grosbill.com/catv2.cgi?tdg=%s&param_ajax=1&classement=%s&filtre_type_produit=%s&mode=listing&tri_catalogue=w&filtre_page=30'%(catid, catid, catid)
      session.do(Request(nexturl), process_productlist, dict(context, baseurl=nexturl))               

   else:
      for cat in data.xpath("//div[@class='cartouche_box cartouche_box_site_color tdg_navigation']/div/ul/li/a[regexp:test(@href,'grosbill.com\/\d')]"):
         url = cat.xpath("@href").string()
         category = cat.xpath("descendant::text()").string(multiple=True)
         if url not in XCAT and category not in XCATS:
            session.queue(Request(url), process_category, dict(url=url, category='%s|%s'%(context['category'], category)))

def process_productlist(data, context, session):
   cnt = 0
   for prod in data.xpath("//table[@id='listing_mode_display']//div[@class='product_description']"):
      cnt += 1
      url = prod.xpath("descendant::a/@href").string()
      name = prod.xpath("descendant::a//text()").string(multiple=True)
      rated = prod.xpath(" following-sibling::div[@class='ranking_star_content']")
      if url and name and rated:
         session.do(Request(url), process_product, dict(context, url=url, name=name))
   
   if cnt == 30:
      page = context.get('page', 1)
      nexturl = context['baseurl'] + '?page=%s'%(page+1)
      session.queue(Request(nexturl), process_productlist, dict(context, page=page+1))

def process_product(data, context, session):
   product = Product()
   product.name = context['name']
   product.url = context['url']
   product.ssid = re_search_once('-(\d+)-', product.url)
   product.category = context['category']

   process_reviews(data, dict(product=product, url=product.url), session)

   if product.reviews:
      session.emit(product)

def process_reviews(data, context, session):
   product = context['product']

   for cnt, rev in enumerate(data.xpath("//div[@itemprop='reviewRating']/following::body[1]")):
      review = Review()
      review.type = 'user'
      review.url = context['url']
      review.ssid = '%s-%s'%(product.ssid, cnt+1)
      review.title = rev.xpath("descendant::h3/text()").string(multiple=True)

      review.date = rev.xpath("following::body[1]/span[1]/text()").string()
      author = rev.xpath("following::body[1]/span[@itemprop='author']/text()").string()
      if author:
         review.authors.append(Person(name=author, ssid=author))

      summary = rev.xpath("descendant::span[@itemprop='description'][1]/text()").string(multiple=True)
      if summary:
         review.add_property(type='summary', value=summary)

      ratetxt = rev.xpath("descendant::span[@itemprop='ratingValue']/text()").string(multiple=True)
      if ratetxt:
         rate = re_search_once("(\d+)", ratetxt)
         if rate:
            review.grades.append(Grade(type='overall', name='Note', value=float(rate), best=20.0))

      for cnt2, g in enumerate(rev.xpath("descendant::th")):
         name = g.xpath("descendant::text()").string(multiple=True)
         ratetxt = g.xpath("following::tr[1]/td[%d]/span/@class"%(cnt2)).string()
         if name and ratetxt:
            rate = re_search_once('ranking_star(\d)', ratetxt)
            if rate:
               review.grades.append(Grade(name=name, value=float(rate), best=5.0))

      if review.grades and review.properties:
         product.reviews.append(review)

def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=20000)]
    session.queue(Request('http://www.grosbill.com/'), process_frontpage, {})
    #session.queue(Request('http://www.grosbill.com/3-ordinateur_portable-ordi_portable-type-ordinateurs'), process_productlist, dict(category='Ordinateurs Portables'))