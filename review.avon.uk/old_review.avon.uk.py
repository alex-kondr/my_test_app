# -*- coding: utf8 -*-
from agent import *
from models.products import *
import random
import yaml
import simplejson


def run(context: dict[str, str], session: Session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://avon.uk.com/collections/fragrance/womens_fragrance', use="curl"), process_productlist, dict(category='Womens Fragrance',cid='304-377'))
    session.queue(Request('https://avon.uk.com/collections/body-sprays-mists', use="curl"), process_productlist, dict(category='Body Sprays',cid='304-378'))
    session.queue(Request('https://avon.uk.com/collections/fragrance/mens_aftershave', use="curl"), process_productlist, dict(category='Mens Fragrance',cid='304-482'))

    #url = 'https://www.avon.uk.com/product/304-377-14936/perfume/far-away/far-away-rebel-diva-for-her-perfume-set'
    #session.queue(Request(url), process_product, dict(category='category', url=url, name='name', pid='14936'))


def process_productlist(data: Response, context: dict[str, str], session: Session):
    for link in data.xpath('//div[@class="product-details"]//node()[@class="product-title"]//a'):
        url = link.xpath('@href').string()
        name = link.xpath('text()').string()
        if url and name:#and not session.seen(url):
            session.queue(Request(url, use="curl"), process_product, dict(context, url=url, name=name))

    # Next page
    next=data.xpath('//li[@class="pagination-btn next"]//a//@href').string()
    if next:
        session.queue(Request(next, use="curl"), process_productlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.manufacturer = "Avon"
    product.category = context['category']

    pid = data.xpath('//div[@data-product-id]//@data-product-id').string()
    if pid:
        product.ssid = pid

        revurl = 'https://staticw2.yotpo.com/batch/wLzCgzI3qtYaGL8IebLnz3ZEkclM5g2BAA6PvG6L?methods=[{"method":"reviews","params":{"pid":"' + pid + '","order_metadata_fields":{},"index":0,"data_source":"default","page":1,"host-widget":"main_widget","is_mobile":false,"pictures_per_review":10,"sort":"date","direction":"desc","sort direction":["date desc"]}}]&app_key=wLzCgzI3qtYaGL8IebLnz3ZEkclM5g2BAA6PvG6L&is_mobile=false&widget_version=2020-05-13_16-08-31&abc='+str(random.randint(1,999999)+random.randint(1,9999999))

        session.do(Request(revurl), process_reviews, dict(context, product=product, base_url=revurl, page=1))

    if product.reviews:
        session.emit(product)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    html_data = data.content
    json_data = simplejson.loads(html_data)
    html_data = json_data[0]['result']
    html_data= '<html><head></head><body>\n' + html_data + '\n</body></html>'
    data = data.parse_fragment(html_data)

    cnt = 0
    for link in data.xpath('//div[contains(@class,"yotpo-review ")][@data-review-id]'):
        cnt += 1
        review=Review()
        review.product=product.name
        review.url=product.url
        review.type='user'
        review.ssid = link.xpath('@data-review-id').string()

        # Title
        title = data.xpath('descendant::div[contains(@class,"content-title")]//text()').string()

        # Publish date
        pub_date=link.xpath('descendant::span[contains(@class,"yotpo-review-date")]//text()').string()
        if pub_date:
            review.date=pub_date.replace(',','')
        else:
            review.date='unknown'

        # Author
        author=link.xpath('descendant::span[contains(@class,"yotpo-user-name")]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            review.authors.append(Person(name='unknown', ssid='unknown'))

        # Grades
        overall=link.xpath('descendant::span[@class="sr-only"]//text()').string()
        if overall:
            overall = re_search_once('(\d+).', overall)
            if overall:
                review.grades.append(Grade(name='Overall Rating', type='overall', value=overall, best=5))

        # Summary
        summary=link.xpath('descendant::div[@class="content-review"]//text()').string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary',value=summary))

            product.reviews.append(review)
            print review.ssid, summary

    print 'CNT', cnt
    if cnt == 6:
        page = context['page'] + 1
        print 'NEXT:', page
        url = context['base_url'].replace('"page":1','"page":'+str(page))
        url = url.split('&abc=')[0] + '&abc='+str(random.randint(1,999999)+random.randint(1,9999999))
        session.do(Request(url), process_reviews, dict(context, page=page))