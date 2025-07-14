from agent import *
from models.products import *
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


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.cowcotland.com/articles/', use='curl', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="categories"]/li/a')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="live_infos"]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    if revs:
        page = context.get('page', 1) + 1
        next_url = context['cat_url'] + 'page{}/'.format(page)
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test ', '').split(', ')[0].split(' : ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat'].split(' (', '')[0].strip()
    product.manufacturer = data.xpath('//tr[contains(., "Fabricant")]/td[not(contains(., "Fabricant"))]//text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    awards = data.xpath('//img[regexp:test(@src, "/images/awards/|/images/test/klevv/crasv")]/@src')
    for award in awards:
        award = award.string()
        review.add_property(type='awards', value=award)

    pros = data.xpath('//tbody[.//td[regexp:test(normalize-space(.), "Pour$")]]//td[not(regexp:test(normalize-space(.), "Pour$"))][1]//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tbody[.//td[contains(., "Contre")]]//td[not(contains(., "Contre"))][2]//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    excerpt = data.xpath('//div[@class="artcontent"]/p[not(regexp:test(., "les spécifications|Fiche technique") or @class)]//text()').string(multiple=True)

    pages = data.xpath('//select[@name="selpage"]/option')
    if len(pages) > 1:
        for page in pages:
            title = page.xpath('text()').string()
            page_url = 'https://www.cowcotland.com' + page.xpath('@value').string()
            review.add_property(type='pages', value=dict(title=title, url=page_url))

    if len(pages) > 1:
        session.do(Request(page_url, use='curl', max_age=0), process_review_last, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    strip_namespace(data)

    review = context['review']

    awards = data.xpath('//img[regexp:test(@src, "/images/awards/|/images/test/klevv/crasv")]/@src')
    for award in awards:
        award = award.string()
        review.add_property(type='awards', value=award)

    pros = data.xpath('//tbody[.//td[regexp:test(normalize-space(.), "Pour$")]]//td[not(regexp:test(normalize-space(.), "Pour$"))][1]//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tbody[.//td[contains(., "Contre")]]//td[not(contains(., "Contre"))][2]//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="artcontent"]/p[not(contains(., "les spécifications|Fiche technique") or @class)]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion.replace('Conclusion ', '')).strip()
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)

