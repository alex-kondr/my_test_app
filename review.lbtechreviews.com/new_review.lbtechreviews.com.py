from agent import *
from models.products import *
import simplejson
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.lbtechreviews.com/test', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats_json = data.xpath('//script[contains(., "window.FWP_JSON =")]/text()').string()
    cats_html = simplejson.loads(cats_json.split('window.FWP_JSON = ')[-1].split('window.FWP_HTTP = ')[0].replace('\\\\', '\\').strip(' ;')).get('preload_data', {}).get('facets', {}).get('testkategorier')
    new_data = data.parse_fragment(cats_html)

    cats = new_data.xpath('//div[@class="facetwp-link"]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)
        prods_cnt = int(cat.xpath('span/text()').string().strip('( )'))
        cat_data = cat.xpath('@data-value').string()
        options = '''--compressed -X POST -H 'Accept-Encoding: deflate' --data-raw '{"action":"facetwp_refresh","data":{"facets":{"testkategorier":["''' + cat_data + """\"],"ikontype":[],"tester":[],"sideviser":[]},"frozen_facets":{},"http_params":{"get":{"fwp_testkategorier":"computer"},"uri":"test","url_vars":[]},"template":"wp","extras":{"sort":"default"},"soft_refresh":0,"is_bfcache":1,"first_load":0,"paged":1}}'"""
        url = 'https://www.lbtechreviews.com/test?fwp_testkategorier=' + cat_data
        session.queue(Request(url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(cat=name, cat_data=cat_data, prod_url=url, prods_cnt=prods_cnt))


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json.get('template'))

    revs = new_data.xpath('//div[contains(@class, "template")]/a')
    for rev in revs:
        title = rev.xpath('following-sibling::div[1]//span[@class="prodtitle"]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    offset = context.get('offset', 0) + 15
    if offset < context['prods_cnt']:
        next_page = context.get('page', 1) + 1
        options = '''--compressed -X POST -H 'Accept-Encoding: deflate' --data-raw '{"action":"facetwp_refresh","data":{"facets":{"testkategorier":["''' + context['cat_data'] + """\"],"ikontype":[],"tester":[],"sideviser":[]},"frozen_facets":{},"http_params":{"get":{"fwp_testkategorier":"computer","fwp_paged":\"""" + str(next_page) + """\"},"uri":"test","url_vars":[]},"template":"wp","extras":{"sort":"default"},"soft_refresh":1,"is_bfcache":1,"first_load":0,"paged":""" + str(next_page) + """}}'"""
        next_url = context['prod_url'] + '&fwp_paged=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(context, page=next_page, offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' review', '').replace(' Review', '').strip()
    product.url = data.xpath('//a[contains(., "Official site")]/@href').string() or context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//div[header[contains(@class, "entry-header")]]/div/h2/text()').string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@class="published"]/text()').string()
    if date:
        review.date = date.replace('Published', '').split(' - ')[0].strip()

    author = data.xpath('//a[@itemprop="author"]/text()').string()
    author_url = data.xpath('//a[@itemprop="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//img[@alt="Karakter"]/@src').string()
    if grade_overall:
        grade_overall = grade_overall.split('/EN_')[-1].replace('.png', '')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    pros = data.xpath('//span[i[contains(@class, "advikonplus")]]/span|//div[@class="advantages"]/div')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[i[contains(@class, "advikonminus")]]/span|//div[@class="disadvantages"]/div')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[header[contains(@class, "entry-header")]]/div/p//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(., "Conclusion")]]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]//text()[not(contains(., "Conclusion"))]').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[contains(., "Conclusion")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="thecontent"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
