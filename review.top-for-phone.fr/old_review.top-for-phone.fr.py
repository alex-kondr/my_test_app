from agent import *
from models.products import *
import re, simplejson


def process_revlist(data, context, session):
    for rev in data.xpath("//h2[@class='post-box-title']/a"):
        name = rev.xpath("text()").string(multiple=True)
        url = rev.xpath("@href").string(multiple=True)
        if url and name:
           session.queue(Request(url, use="curl"), process_review, dict(url=url, name=name))

    next = data.xpath("//span[@id='tie-next-page']//@href").string()
    if next:
        session.queue(Request(next, use="curl"), process_revlist, context)


def process_review(data, context, session):
    content = simplejson.loads(data.xpath("//script[@type='application/ld+json'][contains(., 'dateCreated')]/text()").string())

    product = Product()
    product.name = context['name'].split("Test du")[-1].split(":")[0]
    product.category = 'Smartphone'
    product.url = context['url']
    product.ssid = context['url'].split("/")[-1]

    manufacturer = data.xpath("//div[@class='content']/div[@id='crumbs']/span[3]/a/text()").string()
    if manufacturer and '-' in manufacturer:
        product.manufacturer = manufacturer.split("-")[-1]

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = context['url']
    review.ssid = product.ssid
    review.date = content['datePublished'].split("T")[0]

    review.authors.append(Person(name=content['author']['name'], profile_url=content['author']['url'], ssid=content['author']['url'].split("/")[-1]))

    for score in data.xpath("//div[@class='review-item']//h5//text()"):
        value = re_search_once("(\d+)", score.string())
        title = score.string().split(" -")[0]
        if value and title:
            review.grades.append(Grade(name=title, value=value, best=100))

    overall = data.xpath("//div[@class='review-final-score']/h3/text()").string()
    if overall:
        review.grades.append(Grade(type='overall', value=int(overall), best=100))

    pros = data.xpath("//div[@class='entry']/ul/li[strong[contains(., 'plus')]]/text()").string(multiple=True)
    if pros:
        review.properties.append(ReviewProperty(type='pros', value=pros))

    cons = data.xpath("//div[@class='entry']/ul/li[strong[contains(., 'moins')]]/text()").string(multiple=True)
    if cons:
        review.properties.append(ReviewProperty(type='cons', value=cons))

    conclusion = data.xpath("//*[contains(.,'Conclusion') or contains(.,'En conclusion')]/following::p[ancestor::div/@class = 'entry']//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    excerpt = data.xpath("//div[@class='post-inner']/div[@class='entry']/p//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, "")
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
 
    product.reviews.append(review)
    session.emit(product)


def run(context, session):
    session.queue(Request("http://www.top-for-phone.fr/category/tests", use="curl"), process_revlist, {})
