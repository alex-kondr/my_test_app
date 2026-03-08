from agent import *
from models.products import *
import simplejson


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
    session.queue(Request('https://www.macrumors.com/review/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('(//h2|//h3)/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    rev_json = data.xpath("""//script[contains(., '"@type": "Product"')]/text()""").string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

    product = Product()
    product.ssid = context['url'].split('/')[-2]

    if rev_json:
        product.name = rev_json.get('name')
        product.manufacturer = rev_json.get('brand')

    if not product.name:
        product.name = context['title'].split(' Review: ')[0].split(' Reviews: ')[0].split(' Review ')[0].replace('Review: ', '').strip()

    product.url = data.xpath('//h2[contains(., "How to Buy")]/following-sibling::p/a/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[contains(., "Tags:")]/a[not(regexp:test(., "review|Skip to Content|Guide", "i"))][last()]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[time]/a[@rel="author"]/text()').string()
    author_url = data.xpath('//div[time]/a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    if rev_json:
        grade_overall = rev_json.get('Review', {}).get('reviewRating', {}).get('ratingValue')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('(//p[contains(., "Pros:")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[contains(., "Cons:")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if rev_json:
        summary = rev_json.get('description')
        if summary:
            summary = summary.replace('\r', '').replace('\n', '').strip()
            if summary:
                review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Bottom Line")]/following-sibling::p[not(preceding::h2[regexp:test(., "Where to Buy|How to Buy")] or regexp:test(., "Pros:|Cons:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Bottom Line")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//article/div/p|//article/div/blockquote)[not(preceding::h2[regexp:test(., "Where to Buy|How to Buy")] or regexp:test(., "Pros:|Cons:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
