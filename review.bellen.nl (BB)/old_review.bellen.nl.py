#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session): 
    session.queue(Request('https://www.bellen.com/reviews'), process_revlist, {})
    # session.queue(Request('https://www.bellen.com/mobiele-telefoon/oneplus/3/review'), process_product, dict(url='https://www.bellen.com/mobiele-telefoon/oneplus/3/review', name='Toestelreview Oneplus 3'))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//a[@class='o-list-links__item c-link--cta']")
    for rev in revs:
        name = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.ssid = context['url'].replace("https://www.bellen.com/", "").replace("/", "-")
    product.category = 'Mobiele telefoons, tablets en phablets'
    product.url = context['url']

    product.name = context['name'].split(" review")[0].split(" Review")[0].split(": ")[0].split(" en")[0].split(" incl.")[0]
    if "Review " in product.name:
        product.name = product.name.split("Review ")[1]
    if "nieuwe " in product.name:
        product.name = product.name.split("nieuwe ")[1]
    
    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    date = data.xpath("//p[contains(.,'Geactualiseerd: ')]//text()").string()
    if date:
        date = date.split("Geactualiseerd: ")[1].split(" ")[0]
        if date:
            review.date = date
    
    conclusion = data.xpath("//div[@id='js-reviews-wrapper']//h2[contains(.,'Conclusie')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.split("Geactualiseerd")[0].strip()
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    excerpt = data.xpath("//div[@id='js-reviews-wrapper']//p//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        
        excerpt = excerpt.split("Geactualiseerd")[0].strip()

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    
        product.reviews.append(review)
        session.emit(product)
