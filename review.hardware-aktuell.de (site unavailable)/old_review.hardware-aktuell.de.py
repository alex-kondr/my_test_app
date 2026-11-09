from agent import *
from models.products import *


def process_indexpage(data: Response, context: dict[str, str], session: Session):
   for u in data.xpath('//div[@class="greybox_artikel"]//li/h3/a[not(regexp:test(text(),"Veranstaltungen|Alle Kategorien"))]'):
       url = u.xpath('@href').string()
       catName = u.xpath('text()').string()
       session.queue(Request(url), process_page, dict(context, catName=catName ) )


def process_page(data: Response, context: dict[str, str], session: Session):
   for u in data.xpath('//div[@class="box_links" or @class="box_rechts"]/h2/a'):
       url = u.xpath('@href').string()
       rName = u.xpath('.//text()').string()
       session.queue(Request(url), process_post, dict(context, rUrl=url, rName=rName) )

   for p in data.xpath('//div[@class="center"]/a[contains(@href,"seite=") and contains(b/text(),"chste Seite")]'):
       pUrl = p.xpath('@href').string()
       session.queue(Request(pUrl), process_page, dict(context))
        

def process_post(data: Response, context: dict[str, str], session: Session):
    rTitle = context['rName']
    pCategory = context['catName']
    date = data.xpath('//td[b/text()="Publiziert:"]/following-sibling::td/h3/text()').string(multiple=True)
    author = data.xpath('//td[b/text()="Autor:"]/following-sibling::td/h3/text()').string()
    excerpt = data.xpath('/descendant::div[@id="hauptspalte"][1]/descendant::text()[string-length(normalize-space(.))>150][1]').string(multiple=True)
  
    pName = rTitle.split(" – ")[0].split(" - ")[0].split(" im Test")[0].split(" im Praxistest")[0].split(" im Vergleich")[0].split(" im Kurztest")[0].split(": Ein Alleskönner")[0]
    if "Im Kurztest: " in pName:
        pName = pName.split("Im Kurztest: ")[1]
    if "Neues Flaggschiff: " in pName:
        pName = pName.split("Neues Flaggschiff: ")[1]
    if "Speicherkarten: " in pName:
        pName = pName.split("Speicherkarten: ")[1]
    if "Roundup: " in pName:
        pName = pName.split("Roundup: ")[1]

    review = Review()
    review.title = rTitle
    review.ssid = review.title
    review.date = date
    review.type = "pro" #site's authors...
    review.authors.append(Person(name=author,ssid=author))
    review.properties.append(ReviewProperty(type="excerpt", value=excerpt))
    review.url = context['rUrl']
    pr = Product(name=pName, ssid=review.ssid, url=review.url)
    pr.reviews.append(review)
    pr.category = pCategory

    urls = []
    urls.append(context['rUrl'])
    for u in data.xpath('//div[@class="greybox_artikel"]/ul/li/h3[not(@class)]/a'):
        urls.append(u.xpath('@href').string())
    durls = []
    i=1
    for u in urls:
        durls.append({"url":u, "title":rTitle+" - Seite "+str(i)})
        i=i+1
    review.properties.append(ReviewProperty(type="pages", value=durls))
    
    if len(urls)>1:
        i = 1
        while i < len(urls):
           session.do(Request(urls[i]), process_getConcl, dict(context, review=review))
           i = i + 1
    else:
        process_getConcl(data, dict(context, review=review), session)

    session.emit(pr) 


def process_getConcl(data: Response, context: dict[str, str], session: Session):
   err = 0
   try:
      concl = data.xpath('/descendant::div[@id="hauptspalte"][1]/descendant::text()[string-length(normalize-space(.))>150 and preceding::h3[regexp:test(.,"Fazit")]]').string(multiple=True)
   except:
      err = 1
   if err == 0:
      if not concl:
         concl = data.xpath('/descendant::div[@id="hauptspalte"][1]/descendant::text()[string-length(normalize-space(.))>150 and preceding::b[regexp:test(.,"Fazit")]]').string(multiple=True)
         if concl and len(concl)>15:
            context['review'].properties.append(ReviewProperty(type="conclusion", value=concl))


def run(context: dict[str, str], session: Session):
   session.queue(Request('http://www.hardware-aktuell.com/artikel/'), process_indexpage, {})