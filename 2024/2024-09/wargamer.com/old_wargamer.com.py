from agent import *
from models.products import *
import simplejson


X_URLS = [
    'https://www.wargamer.com/best-napoleonic-games',
    'https://www.wargamer.com/panzer-corps-2/dlc-axis-operations-1941-announcement',
    'https://www.wargamer.com/panzer-corps-2/review',
    'https://www.wargamer.com/panzer-corps-2/axis-operations-1941-review'
]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    options = '-X POST -d "action=new_infinite_scroll&flow_type=post_type&pid=54&index_page=1&index_home=0"'
    session.queue(Request("https://www.wargamer.com/wp-admin/admin-ajax.php", use="curl", options=options, max_age=0, force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    resp = simplejson.loads(data.content)
    try:
        html = resp.get("html")
    except:
        return      # last page

    html = data.parse_fragment(html)

    revs = html.xpath("//article")
    for rev in revs:
        title = rev.xpath("following-sibling::h2[1]/a/text()").string()
        url = rev.xpath("following-sibling::h2[1]/a/@href").string()
        if url not in X_URLS:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    page = context.get("page", 0) + 1
    options = '-X POST -d "action=new_infinite_scroll&flow_type=post_type&pid=54&index_page={}&index_home={}"'.format(str(page + 1), str(page))
    session.do(Request("https://www.wargamer.com/wp-admin/admin-ajax.php", use="curl", options=options, max_age=0, force_charset='utf-8'), process_revlist, dict(page=page))


def process_review(data, context, session):
    if 'Best ' in context['title'] or 'The best ' in context['title']:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].split(" Review –")[0].split(' review –')[0]
    product.category = "Games"

    product.url = data.xpath('//div[@class="entry-content"]//div[@data-afflink]/@data-afflink').string()
    if not product.url:
        product.url = context['url']

    product.ssid = context['url'].split('/')
    if product.ssid[-1] in ['preview', 'review']:
        product.ssid = product.ssid[-2]
    else:
        product.ssid = product.ssid[-1]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]').first()
    if author:
        author_name = author.xpath('text()').string().strip()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split("/")[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, url=author_url))

    grade_overall = data.xpath('//div[@class="score_wrap"]//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//p[@class="caption"]//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath('//h2[contains(., "Final verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="entry-content"]//p[@class="summary"]/text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(preceding-sibling::h2[contains(., "Final verdict")])][not(@class="summary")]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    prods = data.xpath('//div[@class="entry-content"]/h2')
    for prod in prods:
        product = Product()

        name = prod.xpath('text()').string()
        if not name:
            continue

        product.name = name.split('. ')[-1]
        product.category = "Games"

        product.url = prod.xpath('following-sibling::div[@data-afflink][1]/@data-afflink').string()
        if not product.url:
            product.url = context['url']

        product.ssid = '_'.join(product.name.strip().replace('-', '_').replace(',', '').replace('–', '').replace('!', '').replace('?', '').replace('"', '').replace("'", '').replace('.', '').replace('__', '_').lower().split())

        review = Review()
        review.title = context['title']
        review.url = context['url']
        review.ssid = product.ssid
        review.type = 'pro'

        date = data.xpath('//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//a[@rel="author"]').first()
        if author:
            author_name = author.xpath('text()').string().strip()
            author_url = author.xpath('@href').string()
            author_ssid = author_url.split("/")[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, url=author_url))

        excerpt = ''
        text = prod.xpath('following-sibling::*[not(a[@class="site_jumplink"])][not(a[@rel="nofollow noopener "])][not(strong[contains(., "specs:")])]')
        for line in text:
            if line.xpath('self::h2'):
                break
            elif line.xpath('self::p'):
                line = line.xpath('.//text()')
                if line:
                    excerpt += line.string(multiple=True)

        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

            session.emit(product)
