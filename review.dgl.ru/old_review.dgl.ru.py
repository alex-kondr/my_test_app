import string
from agent import *
from models.products import *
import re
import json
from Ft.Xml.Domlette import NonvalidatingReader

debug = True

def run(context, session): 
    session.queue(Request('http://www.dgl.ru/reviews/'), process_frontpage, {'page': 1, 'offset': 0})

def process_frontpage(data, context, session):
    count = 0 
    for p in data.xpath("//ul[@class='a-items']/li/a[@class='a-link']"):
        count += 1
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0][regexp:test(., '[Оо]бзор')]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    if count == 11 or context['page'] == 1:
        page = context['page'] + 1
        offset = context['offset'] + 11
        formdata = {}
        formdata['page'] = page
        formdata['offset'] = offset
        formdata['tagName'] = "reviews"
        formdata['type'] = "byTag"
        url = 'https://www.dgl.ru/load_more_items?type=byTag&tagName=reviews&offset=' + str(offset) + '&page=' + str(page)
        session.queue(Request(url, max_age=0, data=formdata, method='POST'), process_next_page, dict(page=page, offset = offset))

def process_next_page(data, context, session):
    jsonArr = json.loads(data.content)
#    print jsonArr
    print jsonArr['count']
    if jsonArr['count'] > 0:
        offset = context['offset']
        offset += jsonArr['count']

        try:
            content = NonvalidatingReader.parseString(unescapeStr(jsonArr['articles'].encode('utf-8')))
        except: 
            page = context['page'] + 1
            formdata = {}
            formdata['page'] = page
            formdata['offset'] = offset
            formdata['tagName'] = "reviews"
            formdata['type'] = "byTag"
            url = 'https://www.dgl.ru/load_more_items?type=byTag&tagName=reviews&offset=10&page=' + str(page)
            session.queue(Request(url, max_age=0, data=formdata, method='POST'), process_next_page, dict(page=page, offset = offset))

            return
        for p in content.xpath("//ul[@class='a-items']/li/a[@class='a-link']"):
            context['url'] = None
            context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]")[0].nodeValue
            url = p.xpath("@href")[0].nodeValue
            context['name'] = context['name'].strip()
            if context['name'] and url:
                context['url'] = 'http://www.dgl.ru' + url.strip()
                if re_search_once('(obzor)', context['url']):
                    session.queue(Request(context['url']), process_product, context)

        page = context['page'] + 1
        formdata = {}
        formdata['page'] = page
        formdata['offset'] = offset
        formdata['tagName'] = "reviews"
        formdata['type'] = "byTag"
        url = 'https://www.dgl.ru/load_more_items?type=byTag&tagName=reviews&offset=10&page=' + str(page)
        session.queue(Request(url, max_age=0, data=formdata, method='POST'), process_next_page, dict(page=page, offset = offset))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = data.xpath("//ul[@class='dgl-articles-tags']/li[a][1]//text()[string-length(normalize-space(.))>0]").string()
    if not category:
        return False
    product.category = Category(name = category)
    product.ssid = re_search_once('(\d+)\.htm', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='article-info']/span[@class[regexp:test(., 'doc-time')]]/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//div[@class='article-info']/span[@class='authors']/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class='article-body']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='annotation']/p//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@class='article-body']/h2[regexp:test(., 'купить или нет')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))
    for pros in data.xpath("//p[regexp:test(., 'Достоинства')]/following-sibling::*[1][self::ul]/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Достоинства"))
    for cons in data.xpath("//p[regexp:test(., 'Недостатки')]/following-sibling::*[1][self::ul]/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Недостатки"))

    product.reviews.append(review)
    session.emit(product)

def unescapeStr(str):
    codes = (
            ("'", "\\'"),
            ('"', '\\"'),
            ('/', '\/'),
            ('', '\\n'),
        )

    for code in codes:
        str = str.replace(code[1], code[0])

    return str