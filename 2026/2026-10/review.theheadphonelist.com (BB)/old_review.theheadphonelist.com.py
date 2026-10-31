#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request("https://theheadphonelist.com/category/reviews/"), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('(//li[contains(@class, "current-menu-item")])[1]/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        url = cat.xpath('a/@href').string()

        subcats = cat.xpath('ul[@class="sub-menu elementor-nav-menu--dropdown"]/li/a')
        if subcats:
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_revlist, dict(cat=name + "|" + subcat_name))
        else:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@id="ms-listing-grid"]//div[@class="elementor-widget-wrap elementor-element-populated"]')
    for rev in revs:
        title = rev.xpath('.//h3/a//text()').string()
        url = rev.xpath('.//h3/a/@href').string()
        if url and not session.seen(url):
            session.queue(Request(url), process_multiple_revs, dict(context, title=title, url=url))


def process_multiple_revs(data: Response, context: dict[str, str], session: Session):
    prod_url = context.get('prod_url')
    if not prod_url:
        prod_url = data.xpath('//a[contains(@rel, "noreferrer")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//a[contains(@rel, "noopener")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(., "purchased from")]//a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(., "available from")]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(., "can purchase")]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//a[contains(., "Buy from")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//a[contains(., "here")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "from this link:")]/following-sibling::p[1]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//a[contains(text(), "Buy at ")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "m these links:")]/following-sibling::p[1]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "Order one from here:")]/following-sibling::div/blockquote/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "yourself from here:")]/following-sibling::p[1]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "sells for ")]/a/@href').string()
    if not prod_url:
        prod_url = data.xpath('//p[contains(text(), "Get one from here:")]/following-sibling::p[1]/a/@href').string()

    rev = context.get('review')
    if not rev:
        rev = dict()

    rev['date'] = data.xpath('//li[@itemprop="datePublished"]/span/text()').string(multiple=True)

    author = data.xpath('//div[@class="elementor-author-box__text"]').first()
    if author:
        rev['author'] = author.xpath('h4//text()').string()
        rev['author_url'] = author.xpath('a/@href').string()

    pros = rev.get('pros')
    if not pros:
        pros = data.xpath('//p[contains(., "Pros –")]/following-sibling::p[1]//text()').string(multiple=True)
        if pros:
            rev['pros'] = pros.split(', ')
        else:
            pros = ""

    if not pros:
        pros_multiple = data.xpath('//p[contains(., "Pros:")]/following-sibling::ul/li')
        if pros_multiple:
            pros_lst = []
            for pro in pros_multiple:
                pro = pro.xpath('.//text()').string(multiple=True)
                pros_lst.append(pro)
            rev['pros'] = pros_lst

    cons = rev.get('cons')
    if not cons:
        cons = data.xpath('//p[contains(., "Cons –")]/following-sibling::p[1]//text()').string(multiple=True)
        if cons:
            rev['cons'] = cons.split(', ')
        else:
            cons = ""
    
    if not cons:
        cons_multiple = data.xpath('//p[contains(., "Cons:")]/following-sibling::ul/li')
        if cons_multiple:
            cons_lst = []
            for con in cons_multiple:
                con = con.xpath('.//text()').string(multiple=True)
                cons_lst.append(con)
            rev['cons'] = cons_lst

    grade_overall = data.xpath('//strong[contains(., "Verdict ")][contains(., "/")]//text()').string()
    if grade_overall and "/" in grade_overall:
        rev['grade_overall'] = grade_overall.split('/')[0].split('– ')[-1].split('Verdict ')[-1]
        rev['grade_max'] = grade_overall.split('/')[-1].rstrip(',')
    
    summary = rev.get('summary')
    if not summary:
        summary = data.xpath('//p[strong[contains(text(), "Disclaimer –")]]/following-sibling::p[1][not(img)]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//p[contains(., "Disclaimer")]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//em[contains(text(), "DISCLAIMER")]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//p[em[contains(text(), "Preface")]]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('(//div[@class="elementor-widget-container"]//p[not(@class="elementor-heading-title elementor-size-default")])[1]/em//text()').string(multiple=True)
    
    if summary:
        rev['summary'] = summary.split('DISCLAIMER')[-1].split('Preface')[-1].split('Disclaimer')[-1].lstrip(': ')
    else:
        summary = ""


    # In multipage revs first page has short conclusion, but full conclusion always on last page
    conclusion = data.xpath('//p[contains(., "CONCLUSION")][position() = last()]/following-sibling::p[not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")][position() = last()]/following-sibling::p[not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Verdict")][position() = last()]/following-sibling::p[not(img)][not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Closing Thoughts")][position() = last()]/following-sibling::p[not(img)][not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Closing thoughts")][position() = last()]/following-sibling::p[not(img)][not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(text(), "Summary")]/following-sibling::p[not(img)][not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]//text()').string(multiple=True)
    if grade_overall and not conclusion:
        conclusion = data.xpath('//p[contains(., "Verdict")][position() = last() - 1]/following-sibling::p[not(.//a[@rel="noreferrer noopener"])][not(contains(., "purchased from"))][not(contains(., "Buy from"))][not(contains(., "available from"))][not(contains(text(), "template=add to cart"))]/text()').string(multiple=True)
    
    if conclusion:
        conclusion = conclusion.split('Track List –')[0].strip()
        rev['conclusion'] = conclusion
    else:
        conclusion = ""


    short_conclusion = data.xpath('//p[contains(., "Verdict")][1]/following-sibling::p[1]//text()').string(multiple=True)
    if not short_conclusion:
        short_conclusion = ""

    
    excerpt = rev.get('excerpt')
    if not excerpt:
        excerpt = ""


    excerpt_content = data.xpath('//div[@class="elementor-widget-container"]//p[not(@class="elementor-heading-title elementor-size-default")][not(a[contains(., "Buy ")])][not(contains(., "purchased from"))][not(contains(., "available from"))][not(contains(., "Next Page: "))][not(contains(., "Onto the next page"))][not(contains(., "Closing thoughts"))][not(contains(text(), "template=add to cart"))][not(em[contains(text(), "Continue to")])][not(contains(text(), "m these links:"))][not(contains(., "Cons:"))][not(contains(., "Pros:"))]')
    for content in excerpt_content:
        if content.xpath('.//text()'):
            if 'conclusion' in content.xpath('.//text()').string().lower() or 'Track List –' in content.xpath('.//text()').string() or content.xpath('contains(@class, "comment")') or content.xpath('parent::div[contains(@class, "comment")]'):
                break
        
            if content.xpath('strong') and not content.xpath('text()'):
                continue

            if content.xpath('strong/text()') and ' –' not in content.xpath('strong/text()').string() and not content.xpath('strong[contains(., "Verdict ")][contains(., "/")]') or content.xpath('text()') and not content.xpath('strong') and content.xpath('text()').string()[:1] == ',' or content.xpath('.//em') or content.xpath('contains(., "can purchase")') or content.xpath('a/text()'):
                excerpt += " " + content.xpath('.//text()').string(multiple=True)
            elif content.xpath('text()').string() and not content.xpath('a/strong') and not content.xpath('em[contains(text(), "Highly recommended")]') or content.xpath('a[contains(@rel, "noopener")]') :
                excerpt += " " + content.xpath('text()').string(multiple=True)

    if excerpt:
        if conclusion != "":
            excerpt = excerpt.split(conclusion)[0]
        excerpt = excerpt.replace(str(pros), "").replace(str(cons), "").replace(summary, "").replace(short_conclusion, "").rstrip('-~: Pinky_Powers').strip()
        rev['excerpt'] = excerpt

    next_url = data.xpath('//a[contains(text(), "Next Page")]/@href').string() or data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_multiple_revs, dict(context, prod_url=prod_url, review=rev ))
    else:
        context['review'] = rev
        context['prod_url'] = prod_url
        process_review(data: Response, context: dict[str, str], session: Session)


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split('– A Review of the ')[-1].split(' – A Review of ')[-1].split(' review')[0].split(' Review')[0]
    product.category = context['cat']
    product.ssid = context['url'].split('/')[-2]

    product.url = context['prod_url']
    if not product.url:
        product.url = context['url']

    if context['title'].split(' ')[0] == "Review:":
        product.name = context['title'].split('Review: ')[-1]
    
    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.url = context['url']
    review.title = context['title']
    review.date = context['review']['date']

    author = context['review'].get('author')
    if author:
        review.authors.append(Person(name=author, ssid=author, url=context['review']['author_url']))

    grade_overall = context['review'].get('grade_overall')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(context['review']['grade_max'])))

    pros = context['review'].get('pros')
    if pros:
        for pro in pros:
            review.add_property(type='pros', value=pro)

    cons = context['review'].get('cons')
    if cons:
        for con in cons:
            review.add_property(type='cons', value=con)
    
    summary = context['review'].get('summary')
    if summary:
        review.add_property(type='summary', value=summary)
        
    conclusion = context['review'].get('conclusion')
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = context['review'].get('excerpt')
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)