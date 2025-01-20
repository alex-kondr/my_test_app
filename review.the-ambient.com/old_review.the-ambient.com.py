from agent import *
from models.products import *


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='cb-editable']")
    for prod in prods:
        name = prod.xpath(".//h3//text()").string()
        url = prod.xpath(".//a//@href").string()
        session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    nexturl = data.xpath("//link[@rel='next']//@href").string()
    if nexturl:
        session.queue(Request(nexturl, use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].split(" Review")[0].split(" review")[0]
    product.ssid = context['url'].split('/')[-1]
    product.url = context['url']
    product.category = data.xpath("//div[contains(@class, 'breadcrumbs')]//text()").string()

    review = Review()
    review.title = data.xpath("//h1[@class='rich-text__title']//text()").string()
    review.date = data.xpath("//div[contains(@class, 'article-date')]//text()").string(multiple=True).strip()
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    
    author_name = data.xpath("//div[contains(@class, 'article-author')]/a//text()").string()
    author_url = data.xpath("//div[contains(@class, 'article-author')]/a//@href").string()
    if author_name:
        if author_url:
            review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
        else:
            review.authors.append(Person(name=author_name, ssid=author_name))
    
    summary = data.xpath("//h4[contains(@class, 'font-teaser')]//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath("//div[contains(@class, 'review-summary')]//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    grade_overall = len(data.xpath("//div[@class='review-box']//i[@class='icon icon-star-full']"))
    if grade_overall > 0:
        if data.xpath("//i[@class='icon icon-star-half']"):
            grade_overall += 0.5
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath("//div[contains(text(), 'PROS')]/following-sibling::ul[1]/li")
    for pro in pros:
        pro = pro.xpath("text()").string()
        if pro:
            review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//div[contains(text(), 'CONS')]/following-sibling::ul[1]/li")
    for con in cons:
        con = con.xpath("text()").string()
        if con:
            review.add_property(type='cons', value=con)
    
    excerpt = data.xpath("//div[@class='article rich-text']/p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary,'')
        if conclusion:
            excerpt = excerpt.replace(conclusion,'')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt.strip()))

        product.reviews.append(review)
        session.emit(product)


def run(context, session):
    session.queue(Request("https://www.the-ambient.com/reviews", use='curl'), process_prodlist, dict())
