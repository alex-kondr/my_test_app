from agent import *
from models.products import *
import re


def process_index(data, context, session):
    for cat in data.xpath('//div[@id="test2"]//dt/a[regexp:test(text(),"TV - Son|Electrom.nager")]'):
        # catName = cat.xpath('.//text()').string(multiple=True)
        # preceding::h2[1]//text()
        catUrl = cat.xpath('@href').string()
        session.queue(Request(catUrl, use='curl'), process_cat, dict(context, catUrl=catUrl))


def process_cat(data, context, session):
    if data.xpath('//section[@id="niveaux"]//div[@class="univers tiers"]//li/a'):
        # found product list, no more subcateg.
        process_productlist(data, context, session)
        return

    # if no products - go deeper to categories
    for cat in data.xpath('//div[@class="colonne_droite"]//div[@class="description"]/div[@class="sstitre"]/a'):
        catUrl = cat.xpath('@href').string()
        session.queue(Request(catUrl, use='curl'), process_cat, dict(context, catUrl=catUrl))


def process_productlist(data, context, session):
    # captcha
    for cat in data.xpath('//div[@id="fils"]//div[@class="contient"][descendant::img[@class="etoiles"]]/descendant::div[@class="titre"]/span/a'):
        # all products with reviews
        prUrl = cat.xpath('@href').string()
        if prUrl.startswith('+'):
            prUrl = prUrl[1:]
        prName = cat.xpath('text()').string(multiple=True)
        session.queue(Request(prUrl, use='curl'), process_product, dict(context, prUrl=prUrl, prName=prName))

    if data.xpath('//span[@id="numerotation"]/a[text()=">"]'):
        # next page
        nxtLink = data.xpath('//span[@id="numerotation"]/a[text()=">"]/@href')[0].string()
        session.queue(Request(nxtLink, use='curl'), process_productlist, dict(context))


def process_product(data, context, session):
    pr = Product()
    prName = context['prName']
    pr.name = prName
    prUrl = context['prUrl']
    pr.url = prUrl
    pr.ssid = prUrl.split('/')[-2]

    catName = []
    for c in data.xpath('//div[@id="ariane"]//a[position()>1]/text()'):
        catName.append(c.string())
    pr.category = "|".join(catName)

    process_reviews(data, dict(context, pr=pr), session)

    session.emit(pr)


def process_reviews(data, context, session):
    for rev in data.xpath('//div[@class="commentaire"]'):
        review = Review()
        review.type = 'user'
        review.url = context['pr'].url

        revUser = rev.xpath('div[@class="titre"]/span[1]/text()').string().split(":")[-1]
        review.authors.append(Person(name=revUser, ssid=revUser))
        review.date = rev.xpath('div[@class="titre"]/span[2]/text()').string().split(" ")[-1]
        review.ssid = context['pr'].name + "_R_" + revUser + review.date
        review.title = rev.xpath('descendant::div[@class="seconde_colonne"]/span[@class="gras"]/text() ').string()

        cons = data.xpath('descendant::div[@class="plus_moins_colonne2"][2]//text()').strings()
        pros = data.xpath('descendant::div[@class="plus_moins_colonne2"][1]//text()').strings()
        if pros:
            review.properties.append(ReviewProperty(name="Les Plus", type="pros", value=pros))
        if cons:
            review.properties.append(ReviewProperty(name="Les Moins", type="cons", value=cons))

        revText = rev.xpath('div[@class="position"]/div[@class="seconde_colonne"]/span[@class="grand"]/text()').string(
            multiple=True)
        if revText:
            review.add_property(type='summary', value=revText)
        revGrade = \
        rev.xpath('descendant::div[@class="premiere_colonne"][1]/span[@class="gras"][1]/text()').string().split("/")[0]

        review.grades.append(Grade(type='overall', value=float(revGrade), best=5.0))

        context['pr'].reviews.append(review)

    # next?
    # not here for now...


# if data.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a'):
#     #next page
#     nxtLink = data.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@href')[0].string()
#     session.do(Request(nxtLink), process_reviews, dict(context))


def run(context, session):
    session.queue(Request('http://www.but.fr/aide/plan-site.php', use='curl'), process_index, {})


