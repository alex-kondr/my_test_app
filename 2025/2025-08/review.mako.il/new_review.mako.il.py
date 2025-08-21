from agent import *
from models.products import *


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: uzmx=7f900043361c2b-0382-4767-9593-dfed41b041c01-17551552624481262-071dff700320b30a13; __uzma=fcab081e-c214-4281-83f6-b8fcef234a18; __uzmb=1755155263; __uzme=0926; __uzmc=927181077128; __uzmd=1755155263; __uzmf=7f9000fcab081e-c214-4281-83f6-b8fcef234a181-17551552637100-0002256c2973f2dbfd910; __xdst=7f7000d87cafc2-263b-4a16-a052-c1517637b63102175515526394643883-2361eba901c371a114; redPoint=1; __ssds=0; visit_id=84ea6bfe-6f77-4fd7-aa63-15175e83dd4f; visit_timestamp=1755155277635; user_create_date=1755155273008; user_id=a843eb3d937835038b3f79dc1a2200d6; mseid=Wc06943febe81dab09d597a1a26a7eac9c97; __ssuzjsr0=a9be0cd8e; __uzmaj0=fcab081e-c214-4281-83f6-b8fcef234a18; __uzmbj0=1755155266; __uzmcj0=811191052267; __uzmdj0=1755155270; __uzmlj0=xP+am9YS20pzyzZkjipDwc5OOORIGxWubIAVKMuc+8M=; __uzmfj0=7f9000fcab081e-c214-4281-83f6-b8fcef234a181-17551552669133422-000d04bc30e1819438810; uzmxj=7f900043361c2b-0382-4767-9593-dfed41b041c01-17551552669133422-e0e83954b85b66f313'"""


def run(context, session):
    session.queue(Request('https://www.mako.co.il/Tagit/%D7%A1%D7%A7%D7%99%D7%A8%D7%94', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h5/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string().split('?')[0]
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_review, dict(title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.mako.co.il/Tagit/%D7%A1%D7%A7%D7%99%D7%A8%D7%94?page={}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('סקירה: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.htm', '')
    product.category = data.xpath('(//div[contains(@class, "ArticleContent_rightColumn")]/div/a/span[contains(@class, "className")])[last()]/text()').string() or 'טכנולוגיה'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "AuthorSourceAndSponsor_name")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "ציון:") and string-length(.) < 20]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    summary = data.xpath('//p[contains(@class, "ArticleSubtitle_root")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h4[contains(., "סיכום")]/following::p[not(contains(., "הכין לפרסום:") or @class or b)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[contains(., "סיכום")]/preceding::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "HtmlRender_root")]/p[not(contains(., "הכין לפרסום:") or @class or b)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
