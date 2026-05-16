from agent import *
from models.products import *
import simplejson


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
    r.add_header('Accept-Encoding', 'deflate')
    r.add_header('Cookie', '__cf_bm=5_zr.FYsdp1PbNExS96CYcImSPYcWCVlLJde85M.ZBk-1778849205.004714-1.0.1.1-c3ZnTa7HjvD3cCBNdJiVJQNYQk1aFu.abm742UNlUQ8B8v_ZlgaZG_OlPfZ93TnrNLSvxF1hUCaMLOOaEbdOz2jWcczGXcyfTUbPoch3kwcX.gXMpM7MtqIJzIVMxUwh; cf_clearance=tupiONcurEs_gorPhXSj4rSi2sPoJ.z1DG2dtrmbo8k-1778849205-1.2.1.1-El1Nh9chY5RgCo9FJHOHG8bX7X8Nbje_.uUs_YQhHt40t4Dp0k41LDoj76AN0Lv8Th5lJGj35..VdXtw9LJbL1Nh0XbjVk_zhYQ5J8.DgRYrCyLotgXrPZsV5HxZHBzKI3v1.EIddY9NVSo9onb417qpxLMD4kdOGg04YF.gAObyxquwygddLb9XdZzgRPUli7n..AP5_jm12YhsmFr9iOLkf_SDUKhuOR91PdqNgyiD34d1NfGHjdM1iqzOComQhxCFjbNnpfh2daQ0jv6bu5R_skSJtwHpXKB8ekP4_nV4jBV927upI3IBJQSUYz5_jYaINecnyJcJUGW5OqdtpQ')
    return r


def run(context, session):
    session.do(RequestRevs(1), process_revlist, dict())


def process_revlist(data, context, session):
    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    new_data = data.parse_fragment(revs_json.get('html'))

    revs = new_data.xpath('//a[contains(@class, "post-card")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(url=url))

    offset = context.get('offset', 0) + 12
    revs_cnt = context.get('revs_cnt', revs_json.get('total', 0))
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        session.do(RequestRevs(next_page), process_revlist, dict(offset=offset, page=next_page, revs_cnt=revs_cnt))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]//text()').string()
    if not title:
        return

    product = Product()
    product.name = title.replace('I tested the ', '').replace('I tested ', '').replace(' I’ve tested', '').replace('I’ve tested ', '').replace('I used this ', '').replace('I reviewed the ', '').replace(' Review', '').replace(' Review', '').replace(' review', '').replace(' review', '').replace(' to the test', '').strip()
    product.category = 'Camera'

    product.url = data.xpath('//a[contains(@href, "https://amzn.to/")]/@href').string()
    if not product.url:
        product.url = context['url']

    short_link = data.xpath('//link[@rel="shortlink"]/@href').string()
    if short_link:
        product.ssid = short_link.split('=')[-1]
    else:
        product.ssid = context['url'].split('/')[-2].replace('-review', '')

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="hero__date"]/text()').string()

    author = data.xpath('//p[contains(@class, "author-name") and not(contains(., "Camera Jabber Team"))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h2[contains(@class, "sub-heading")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Final Thoughts")]/following-sibling::div//text()[not(contains(., "Amazon Link :") or contains(., "Code ") or contains(., "Discount :") or contains(., "https://amzn.to/"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[(contains(@class, "review-section-content") or contains(@class, "post-content")) and not(preceding-sibling::h2[contains(., "Specification") or contains(., "Final Thoughts")])]/div//text()[not(contains(., "Amazon Link :") or contains(., "Code ") or contains(., "Discount :") or contains(., "https://amzn.to/"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[(contains(@class, "review-section-content") or contains(@class, "post-content")) and not(preceding-sibling::h2[contains(., "Specification") or contains(., "Final Thoughts")])]/p//text()[not(contains(., "Amazon Link :") or contains(., "Code ") or contains(., "Discount :") or contains(., "https://amzn.to/"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
