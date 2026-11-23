#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('http://www.nieuwemobiel.nl/Reviews'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//div[@id='timeline']/div"): 
        url = rev.xpath(".//a/@href").string()
        title = rev.xpath(".//h2//text()").string()
        if url and title:
            session.queue(Request(url), process_review, {'url': url, 'title': title})

    nexturl = data.xpath("//span[@class='current']/following-sibling::*/a/@href").string()
    if nexturl:
       session.queue(Request(nexturl), process_revlist, dict()) 


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(" review")[0].split(" Review")[0]
    product.url = context['url']
    product.ssid = product.url.split("/")[-2]
    product.category = 'Mobiele telefoon'

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath("//time/@datetime").string()
    if date:
       review.date = date.split("T")[0]
    
    grade = data.xpath("//span[@class='subcaption']/text()").string()
    if grade:
        grade_val = grade.split('/')[0].replace(",", ".")
        grade_max = grade.split('/')[1].replace(",", ".")
        review.grades.append(Grade(type='overall', value=float(grade_val), best=float(grade_max)))
   
    summary = data.xpath("//p[@class='intro']//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type="summary", value=summary))

    conclusion = data.xpath("//h2[@id='review-conclusie']/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))
   
    excerpt = data.xpath("//article//p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, "")
        if conclusion:
            excerpt = excerpt.replace(conclusion, "")
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

    pros_list = data.xpath("//ul[@class='prosList']/li/text()")
    for pro in pros_list:
        review.properties.append(ReviewProperty(type="pros", value=pro.string()))  

    cons_list = data.xpath("//ul[@class='consList']/li/text()")
    for con in cons_list:
        review.properties.append(ReviewProperty(type="cons", value=con.string()))                            

    product.reviews.append(review) 
    session.emit(product)
