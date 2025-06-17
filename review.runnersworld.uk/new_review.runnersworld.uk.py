from agent import *
from models.products import *
import simplejson
import re


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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.runnersworld.com/uk/gear/shoes/', use='curl', force_charset='utf-8', max_age=0), process_category, dict(cat='Shoes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/clothes/', use='curl', force_charset='utf-8', max_age=0), process_category, dict(cat='Clothes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/tech/', use='curl', force_charset='utf-8', max_age=0), process_category, dict(cat='Tech'))


def process_category(data, context, session):
    strip_namespace(data)

    data_json = data.xpath('''//script[contains(., '"contentId":"')]/text()''').string()
    if data_json:
        cat_id = simplejson.loads(data_json).get('metadata', {}).get('contentId')
        next_url = 'https://www.runnersworld.com/uk/api/feed-content/?id={}&type=subsection&limit=12&token=2&offset=1&params=%7B%22isHomePage%22%3Afalse%2C%22contentSectionEnabled%22%3Atrue%7D'.format(cat_id)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, cat_id=cat_id))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = simplejson.loads(data.content).get('data', {}).get('feedInfo', [{}])[0].get('feedContent')
    if not revs:
        return

    for rev in revs:
        ssid = str(rev.get('display_id'))
        title = rev.get('metadata', {}).get('short_title')
        url = 'https://www.runnersworld.com/uk/a' + str(ssid)

        if not re.search(r'[Tt]he \d* ?best', title) and 'review' in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, ssid=ssid, url=url))

    offset = context.get('offset', 1) + 12
    next_url = 'https://www.runnersworld.com/uk/api/feed-content/?id={id}&type=subsection&limit=12&token=2&offset={offset}&params=%7B%22isHomePage%22%3Afalse%2C%22contentSectionEnabled%22%3Atrue%7D'.format(id=context['cat_id'], offset=offset)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, offset=offset))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.ssid = context['ssid']
    product.category = context['cat']

    product.name = data.xpath('//h2[contains(@class, "e1bddzxd0")]/text()').string()
    if not product.name:
        product.name = context['title'].replace('Review:', '').replace(' Review', '').split(': ')[0].replace(', reviewed', '').replace(' review', '').strip()

    product.url = data.xpath('//a[contains(., "at Amazon")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@class, "product-link") and contains(., "Buy")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//a[contains(@href, "https://www.runnersworld.com/uk/author/")]')
    for author in authors:
        author_name = author.xpath('.//text()').string(multiple=True)
        author_url = author.xpath('@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-3]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//header//div[h1]//p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Who should buy|verdict", "i")]/following::p[contains(@class, "emevuu60")]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Who should buy|verdict", "i")]/preceding::p[contains(@class, "emevuu60")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body")]/p[contains(@class, "emevuu60")]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace('RW Verdict:', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
