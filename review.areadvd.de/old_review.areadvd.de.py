from agent import *
from models.products import *
import re

from Ft.Xml import ReaderException

debug = True

def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//div[@id='links']//a"):
        cat = rev.xpath("(.)/text()").string(multiple=True)
        url = rev.xpath("(.)/@href").string(multiple=True)
        if url and cat:  
           session.queue(Request(url), process_revlist2, {'cat': cat})

def process_revlist2(data: Response, context: dict[str, str], session: Session):
    cat = context['cat']
    for rev in data.xpath("//div[@class='list-posts']/a[contains(text(),'TEST:')] | //div[@class='list-posts']/a[contains(text(),'Test mit')] | div[@id='rechts']/a | //div[@class='entry']/ul/li/a"):
        name = rev.xpath("(.)/text()").string(multiple=True)
        name = re_search_once("TEST: (.+)", name)
        url = rev.xpath("(.)/@href").string(multiple=True)
        if url and name:  
           session.queue(Request(url), process_review, {'url': url, 'name': name, 'cat': cat})

def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['name']

    review = Review()
    product.reviews.append(review)
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    dateaut = data.xpath("//div[@class='postdate']/text()").string()
    if not dateaut:
       dateaut = data.xpath("//p[contains(text(),'.201')]/text()").string()

    date = re_search_once("(.+) \(", dateaut)
    if date:
       review.date = date
    else:
       dateaut = data.xpath("//p[contains(text(),'200')]/text() | //p[contains(text(),'201')]/text()").string()
       date = re_search_once("\((.+) -", dateaut)
       if date:
          review.date = date
       else:
          date = re_search_once("\((.+)\)", product.name)
          if date:
             review.date = date

    aut = re_search_once("\((.+)\)", dateaut)
    if aut:
       review.authors.append(Person(name = aut, ssid = aut))
    if not aut:
       aut = data.xpath("//p[contains(text(),'Autor: ')]/a/text()").string()
       if aut:
          review.authors.append(Person(name = aut, ssid = aut))

    excerpt = data.xpath("//div[@class='entry']/p/text()").string(multiple=True)
    if excerpt:
       review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    fscore = 0
    for scores in data.xpath("//img[@src='http://www.areadvd.de/lm/bluestar.gif']"):
        fscore += fscore

    if fscore > 0:
       review.grades.append(Grade(type='overall', value = fscore, best = 10))

    text = data.xpath("//div[contains(@class,'twoclick_social_bookmarks_post')]/preceding::p[contains(text(),'+')][1]/text()").join(" | ")
    if not text:
       text = data.xpath("//h5[@align='center']/following::p[contains(text(),'+')][1]/text()").join(" | ")
    if text:
       review.properties.append(ReviewProperty(type='pros', value=text))

    text = data.xpath("//div[contains(@class,'twoclick_social_bookmarks_post')]/preceding::p[contains(text(),'-')][1]/text()").join(" | ")
    if not text:
       text = data.xpath("//h5[@align='center']/following::p[contains(text(),'-')][1]/text()").join(" | ")
    if text:
       review.properties.append(ReviewProperty(type='cons', value=text))

    conclusion = data.xpath("//*[text()='Fazit']/following::p[1]/text() | //*[text()='Fazit']/following::p[2]/text()").string(multiple=True)
    if conclusion:
       review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
 
    session.emit(product)


def run(context: dict[str, str], session: Session):
    session.queue(Request("http://www.areadvd.de/tests/", max_age = 0), process_revlist, {})