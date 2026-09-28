# -*- coding: utf8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers=[SessionBreak(max_requests=30000)]
    session.queue(Request('http://4tochki.ru/'), process_first_page, {})


def process_first_page(data: Response, context: dict[str, str], session: Session):
    for link in data.xpath('//ul[contains(@class, "js-main-nav")]//li[@class="nav-item"]//a'):
        url=link.xpath('@href').string()
        category=link.xpath('span//text()').string()
        if url and category:
            session.queue(Request(url), process_second_page, dict(category=category))


def process_second_page(data: Response, context: dict[str, str], session: Session):
    for link in data.xpath('//div[contains(@class, "flex-column-reverse1")]//div[contains(@class, "col-4 col-md-2")]'):
        url=link.xpath('a//@href').string()
        category=link.xpath('span//text()').string()
        if url and category:
            session.queue(Request(url), process_third_page, dict(context, manufacturer=category))


def process_third_page(data: Response, context: dict[str, str], session: Session):
    cid=data.xpath('//input[@name="goProducer"]//@value').string()
    cname=data.xpath('//input[@name="thread"]//@value').string()
    if cid and cname:
        url = 'http://www.4tochki.ru/catalog/models/list_ajax/?count=0&1=1&params[thread]=' + cname + '&params[goProducer]=' + cid + '&page=1&countOnPage=20'
        # 'http://4tochki.ru/Catalog/models/doModelsSearch.php?count=0&1=1&params[thread]='+cname+'&params[goProducer]='+cid+'&page=1&countOnPage=999'
        session.queue(Request(url, force_charset="utf-8"), process_category, dict(context, cat_url=url, cpage=1))


def process_category(data: Response, context: dict[str, str], session: Session):
    cnt = 0
    for link in data.xpath('//div[contains(@class, "col-6 col-lg-3")]//a[descendant::fullname]'):
        cnt += 1
        name=link.xpath('descendant::text()').string(multiple=True)
        url=link.xpath('@href').string()
        if name and url:
            session.queue(Request(url, force_charset="utf-8"), process_product, dict(context, url=url, name=name))

    if cnt >= 20:
        cpage = context['cpage'] + 1
        next = context['cat_url'].replace('page=1','page='+str(cpage))
        session.queue(Request(next, force_charset="utf-8"), process_category, dict(context, cpage=cpage))


def process_product(data: Response, context: dict[str, str], session: Session):
    product=Product()
    product.name=context['name']
    product.url=context['url']
    product.ssid=product.name + product.url
    product.category=context['category']
    product.manufacturer=context['manufacturer']

    #uri = context['url']+'?showAllOpinions=1'#.replace('/catalog/','/opinions/') +'_page_1?ajax=1'
    #session.browser.use_new_parser = True
    if 'modelSlug=' in data.content:
        model = data.content.split('modelSlug=')[1].split('","')[0]
        rev_url = 'https://www.4tochki.ru/opinions/search/?count=0&modelSlug=' + model + '&sortBy=dt&page=1'
        product.ssid = model.replace('&goProducer=','-')
        session.do(Request(rev_url, force_charset="utf-8"), process_review, dict(context, product=product, page=1, base_url=rev_url))
    else:
        print data.content
    #session.browser.use_new_parser = False

    if product.reviews:
        session.emit(product)


def process_review(data: Response, context: dict[str, str], session: Session):
#    try:
    cnt = 0
    product = context['product']

    for link in data.xpath('//div[@data-opinionid]'):
        cnt += 1
        review=Review()
        review.product=product.name
        review.url=context['url']
        review.type='user'
        review.ssid = link.xpath('@data-opinionid').string() or product.ssid+str(c)

        # Publish date
        pub_date=link.xpath('./span[@class="date"]//text()').string()
        if pub_date:
            review.date=pub_date
            review.ssid += pub_date

        # Author
        author=link.xpath('./span[@class="name"]//text()[string-length(normalize-space(.))>1]').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))
            review.ssid += author

        # Grades
        overall=link.xpath('./div[contains(@class,"rating--")]//@class').string()
        if overall:
            score = float(overall.split('rating--')[1].split(' w')[0])
            review.grades.append(Grade(name='Overall Rating', type='overall', value=score, best=5))

        # Summary
        summary=link.xpath('./div[text()]//text()').string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary',value=summary))

        # Pros
        pros=link.xpath('./div[text()]//b[contains(text(),"Достоинства")]/following-sibling::text()[1]').string(multiple=True)
        if pros:
            #print 'pro', pros
            if summary and pros in summary: summary.replace(pros,'').replace('Достоинства','')
            if ': ' in pros: pros = pros[2:]
            review.properties.append(ReviewProperty(type='pros', value=pros))

        # Cons
        cons=link.xpath('./div[text()]//b[contains(text(),"Недостатки")]/following-sibling::text()[1]').string(multiple=True)
        if cons:
            #print 'con', cons
            if summary and cons in summary: summary.replace(cons,'').replace('Недостатки','')
            if ': ' in cons: cons = cons[2:]
            review.properties.append(ReviewProperty(type='cons', value=cons))

        #print 'sum', summary
        if summary:
            product.reviews.append(review)

    # Next page
    if cnt >= 20:
        page = context['page'] + 1
        next = context['base_url'].replace('page=1', 'page='+str(page))
        session.do(Request(next, force_charset="utf-8"), process_review, dict(context, page=page))
#    except:
#        print 'Not well formed... Skip.'