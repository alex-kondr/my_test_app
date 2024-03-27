import string
from agent import *
from models.products import *
import re, yaml
from Ft.Xml.Domlette import NonvalidatingReader

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('http://www.neowin.net/news/tags/review'), process_frontpage, {'offset': 0})

def process_frontpage(data, context, session):
    has_p = False
    for p in data.xpath("//div[@id='news-content']/article//h3/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)
            has_p = True
    if has_p:
        offset = context['offset'] + 1
        next = 'https://www.neowin.net/news/tags/review?ajax=true&newsOffset=' + str(offset)
        session.queue(Request(next), process_next_page, {'offset': offset})

def process_next_page(data, context, session):
    jstxt = data.content
    jstxt = jstxt.replace('\/', '/')
    try:
        resp = yaml.load(jstxt)
    except:
        print "Failed loading yaml:", data.request_url
        raise
        return
    print resp
    d = resp.get('data', {})
    n = d.get('news', "")
    try:
        xml = data.parse_fragment(n)
    except:
        print "Failed loading yaml:", data.request_url
        raise
        return
    has_p = False
    for p in xml.xpath("//article//h3/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)
            has_p = True
    if has_p:
        offset = context['offset'] + 1
        next = 'https://www.neowin.net/news/tags/review?ajax=true&newsOffset=' + str(offset)
        session.queue(Request(next), process_next_page, {'offset': offset})


def process_product(data, context, session):
    product = Product()
    product.name = re_search_once('(.+)\s+review', context['name'])
    if not product.name:
        product.name = context['name']
    product.url = context['url']
    product.category = Category(name = "Gadgets")
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='article-hero-inner']//time/text()[string-length(normalize-space(.))>0]").string()
    if not review.date:
        review.date = data.xpath("//p[@class='article-meta']//time/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//div[@class='article-hero-inner']//a[@rel='author']").first()
    if not user_data:
        user_data = data.xpath("//p[@class='article-meta']//a[@rel='author']").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/profile\/(\d+)', user.profile_url)
        if not user.ssid:
            user.ssid = get_url_parameter(user.profile_url,'showuser')
        review.authors.append(user)
    excerpt = data.xpath("//div[@itemprop='articleBody']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@itemprop='articleBody']/div[text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//h1//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        s = re_search_once('^[^\:]+\:(.+)', summary)
        if not s:
            s = summary
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=s.strip()))
    conclusion = data.xpath("//div[@itemprop='articleBody']/p[preceding-sibling::*[not(self::p)][regexp:test(., 'Conclusion')]][.//text()[string-length(normalize-space(.))>100]]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='conclusion'), value=conclusion, name = "Conclusion"))
    grade = data.xpath("//meta[@itemprop='ratingValue']/@content ").string()
    best = data.xpath("//meta[@itemprop='bestRating']/@content ").string()
    worst = data.xpath("//meta[@itemprop='worstRating']/@content").string()
    if grade and best and worst:
        grade = re_search_once('(\d+\.*\d*)', grade)
        if grade:
            review.grades.append(Grade(name="Rating", value = grade, worst = worst, best = best, type = 'overall'))

	
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

