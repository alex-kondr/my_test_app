#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.mimundogadget.com/search?max-results=20'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//h1[@class='post-title entry-title']/a"):
        url = rev.xpath("@href").string()
        name = rev.xpath("text()[string-length(normalize-space(.))>1]").string()
        if url and name and not session.seen(url):
            session.queue(Request(url), process_review, dict(url=url, title=name))

    next = data.xpath('//a[@class="blog-pager-older-link"]/@href').string()
    if next:
        session.queue(Request(next), process_revlist, context)


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.url = context['url']
    product.ssid = get_url_parameter(data.xpath('//a[contains(@href,"postID")]/@href').string(), 'postID') or context['url'].split("/")[-1].replace('.html', '')

    name = context['title'].replace('[Review]', '').replace('[Análisis]', '')
    for item in [', un ',', una ',', los ',', dos ',', te ', ', unos ',', ¡']:
        if item in name:
            if len(name.split(item)[0]) == 0:
                name = name.split(item)[1]
            else:
                name = name.split(item)[0]
            break

    product.name = name.replace("[Reseña]", "").replace("[con vídeo]", "").strip().split(": ")[0].split("] ")[-1]
    product.category = '|'.join([cat.string() for cat in data.xpath('//a[@rel="tag"]//text()[string-length(normalize-space(.))>1]') if cat]).replace('Review', '').replace('\n', '') or 'Reviews'

    review = Review()
    review.url = context['url']
    review.ssid = context['url'].split("/")[-1].replace('.html', '')
    review.title = context['title']
    review.type = 'pro'

    # Grades
    overall = data.xpath('//div[@class="rev-score"]//text()').string()
    if overall:
        review.grades.append(Grade(name='Overall Rating', type='overall', value=float(overall), best=10.0))

    for grade in data.xpath('//div[@class="review-item"]//div[@class="review-circle"]'):
        name = grade.xpath('text()').string()
        value = grade.xpath('span//text()').string()
        if value and name:
            review.grades.append(Grade(name=name, value=float(value), best=10.0))

    # Summary
    summary = data.xpath('//div[@class="item-summary"]//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value = summary))

    # Conclusion
    conclusion = data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Conclusión|Conclus|conclus)")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//span[regexp:test(descendant::text(),"(Conclusión|Conclus|conclus)")]/parent::*/following-sibling::*//text()[not(ancestor::script)][not(ancestor::style)][not(ancestor::table)]').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath("//div[contains(@id, 'post-body')]//text()[not(ancestor::script)][not(ancestor::style)][not(ancestor::table)]").string(multiple=True).strip()
    if excerpt:
        if conclusion:
            excerpt = excerpt.split(conclusion)[0]

        if summary:
            excerpt = excerpt.replace(summary, '')

    pros = data.xpath("//div[@class='su-box-title'][contains(., 'Ventajas')]/following::div[@class='su-list'][1]/ul/li")
    if not pros:
        pros = data.xpath("//td[@id='pros']/ul/li[position()>1]")
    for pro in pros:
        if excerpt:
            excerpt = excerpt.replace(pro.xpath(".//text()").string(multiple=True), '')
        review.properties.append(ReviewProperty(type='pros', value=pro.xpath(".//text()").string(multiple=True)))

    cons = data.xpath("//div[@class='su-box-title'][contains(., 'Desventajas')]/following::div[@class='su-list'][1]/ul/li")
    if not cons:
        cons = data.xpath("//td[@id='cons']/ul/li[position()>1]")
    for con in cons:
        if excerpt:
            excerpt = excerpt.replace(con.xpath(".//text()").string(multiple=True), '')
        review.properties.append(ReviewProperty(type='cons', value=con.xpath(".//text()").string(multiple=True)))

    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    product.reviews.append(review)
    session.emit(product)
