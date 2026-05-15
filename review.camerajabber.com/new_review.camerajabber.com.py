from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def RequestRevs(page):
    url = "https://camerajabber.com/wp-admin/admin-ajax.php"
    payload = {
        'action': 'filter_posts',
        'page': str(page),
        'per_page': '12',
        'post_type': 'review',
        'exclude': '[1422485,1422465,1422367,1422368]',
        'search': ''
    }
    r = Request(url, data=payload, method='POST')
    r.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0')
    r.add_header('Accept', '*/*')
    # r.add_header('Accept-Language', 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7')
    r.add_header('Accept-Encoding', 'deflate')
    # r.add_header('Referer', 'https://camerajabber.com/reviews/')
    # r.add_header('Origin', 'https://camerajabber.com')
    # r.add_header('Alt-Used', 'camerajabber.com')
    # r.add_header('Connection', 'keep-alive')
    r.add_header('Cookie', '__cf_bm=5_zr.FYsdp1PbNExS96CYcImSPYcWCVlLJde85M.ZBk-1778849205.004714-1.0.1.1-c3ZnTa7HjvD3cCBNdJiVJQNYQk1aFu.abm742UNlUQ8B8v_ZlgaZG_OlPfZ93TnrNLSvxF1hUCaMLOOaEbdOz2jWcczGXcyfTUbPoch3kwcX.gXMpM7MtqIJzIVMxUwh; cf_clearance=tupiONcurEs_gorPhXSj4rSi2sPoJ.z1DG2dtrmbo8k-1778849205-1.2.1.1-El1Nh9chY5RgCo9FJHOHG8bX7X8Nbje_.uUs_YQhHt40t4Dp0k41LDoj76AN0Lv8Th5lJGj35..VdXtw9LJbL1Nh0XbjVk_zhYQ5J8.DgRYrCyLotgXrPZsV5HxZHBzKI3v1.EIddY9NVSo9onb417qpxLMD4kdOGg04YF.gAObyxquwygddLb9XdZzgRPUli7n..AP5_jm12YhsmFr9iOLkf_SDUKhuOR91PdqNgyiD34d1NfGHjdM1iqzOComQhxCFjbNnpfh2daQ0jv6bu5R_skSJtwHpXKB8ekP4_nV4jBV927upI3IBJQSUYz5_jYaINecnyJcJUGW5OqdtpQ')
    # r.add_header('Sec-Fetch-Dest', 'empty')
    # r.add_header('Sec-Fetch-Mode', 'cors')
    # r.add_header('Sec-Fetch-Site', 'same-origin')
    # r.add_header('Priority', 'u=0')
    # r.add_header('Pragma', 'no-cache')
    # r.add_header('Cache-Control', 'no-cache')
    # r.add_header('TE', 'trailers')
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(RequestRevs(1), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    print data.content
    return

    revs = data.xpath('//a[contains(@class, "post-card")]')
    for rev in revs:
        title = rev.xpath('.//h3/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href|//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('/text()').string()
    author_url = data.xpath('/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    # grade_overall = data.xpath('//text()').string()
    # if grade_overall:
    #     review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h3[contains(text(), "Summary")]]/div//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
