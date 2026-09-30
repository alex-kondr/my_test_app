from agent import *
from models.products import *


def process_page(data: Response, context: dict[str, str], session: Session):
   for u in data.xpath('//p/b/a[regexp:test(text(),"обзор|Обзор|Тест|тест") and not(regexp:test(text()," vs|сравни|Сравни"))]'):
       url = u.xpath('@href').string()
       rName = u.xpath('text()').string()
       session.queue(Request(url), process_post, dict(context, rUrl=url, rName=rName) )

   nxtLink = data.xpath('//p/a[@title="следующая"]/@href').string()
   if nxtLink:
       session.queue(Request(nxtLink), process_page, dict(context))
       
def process_post(data: Response, context: dict[str, str], session: Session):
    rTitle = context['rName']

    author = data.xpath('//div[@id="PgBody"]//p//text()[contains(normalize-space(.),"©")][last()]').string()
    if author:
        author = author.strip("© ,")
    date = data.xpath('//div[@id="PgBody"]//p//text()[regexp:test(.,"\d\d.\d\d.\d\d\d\d")]').string(multiple=True).strip(", ")
    pName = rTitle.replace("Обзор","")
    pCategory = u"Мобильные телефоны"

    excerpt = data.xpath('/descendant::div[@id="PgBody"][1]/descendant::p[string-length(normalize-space(.))>150][1]//text()').string(multiple=True)

  
    concl = data.xpath('/descendant::div[@id="PgBody"][1]/descendant::p[string-length(normalize-space(.))>150][last()]//text()').string(multiple=True)

    review = Review()
    review.title = rTitle
    review.ssid = review.title
    review.date = date
    review.type = "pro" #site's authors...
    review.authors.append(Person(name=author,ssid=author))
    if concl:
        review.properties.append(ReviewProperty(type="conclusion", value=concl))
    review.properties.append(ReviewProperty(type="excerpt", value=excerpt))
    review.url = context['rUrl']
    pr = Product(name=pName, ssid=review.ssid, url=review.url)
    pr.reviews.append(review)
    pr.category = pCategory


    session.emit(pr) 


def run(context: dict[str, str], session: Session):
   session.queue(Request('http://www.mforum.ru/news/archive.htm?c=news%2Ftests&sn=0'), process_page, {})