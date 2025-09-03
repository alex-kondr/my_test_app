from agent import *
from models.products import *
import re


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


def serialize_text(text):
    text = re.sub(r'&([a-zA-Z]+);', lambda match: '&' + match.group(1).lower() + ';', text).replace('<br />', ' ').replace('<br/>', ' ').replace('<br/', ' ').replace("\r", "").replace("\n", "").replace('\t', '').replace('&', '&').replace('°', '°').replace('œ', 'œ').replace('í', 'í').replace('ú', 'ú').replace('“', '"').replace('£', '£').replace('"', '"').replace('à', 'à').replace('é', 'é').replace('á', 'á').replace('´', '́').replace('ã', 'ã').replace('ç', 'ç').replace('ó', 'ó').replace('€', '€').replace('ê', 'ê').replace('è', 'è').replace('’', '’').replace('”', '”').replace(' ', ' ').replace('<', '<').replace('>', '>').replace('‘', '‘').replace('–', '–').replace('ä', 'ä').replace('ß', 'ß').replace('ö', 'ö').replace('ü', 'ü').replace('â', 'â').replace('õ', 'õ').replace('ø', 'ø').replace('…', '…').replace('„', '„').replace('—', '—')
    text = re.sub(r'&#[0-9]+;|&#[xX][0-9a-fA-F]+;', '', text)
    return text


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://fr.audiofanzine.com/'), process_frontpage, {})


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="subcategory-list"]')
    for cat in cats:
        name = cat.xpath('li[contains(@class, "title")]/a/text()').string()

        sub_cats = cat.xpath('li[@class="item-list"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('(div/span[@class="text"]|div/a)/text()').string()

            sub_cats1 = sub_cat.xpath('ul/li/a[@class="text"]')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('div/a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//ul[contains(@class, "items__list")]/li')
    for prod in prods:
        name = prod.xpath('.//h3/text()').string()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "rating")]//span[contains(@class, "count")]/text()').string() or prod.xpath('.//span[@class="mark"]/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.split()[0].strip('( )')
            if int(revs_cnt) > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url'].strip('/')
    product.ssid = data.xpath('//input[@id="product_id"]/@value').string() or product.url.split('/')[-1]
    product.category = context['cat'].replace('…', '').replace('...', '')
    product.manufacturer = data.xpath('//li//span[contains(., "Fabricant :")]/following-sibling::span/text()').string()

    user_revs = data.xpath('//a[contains(text(), "Avis")]/@href').string()
    if user_revs:
        session.do(Request(user_revs), process_reviews, dict(product=product))

    pro_revs = data.xpath('//div[contains(@class, "product-review ")]/a/@href').string()
    if pro_revs:
        session.do(Request(pro_revs), process_pro_review, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//ul[@class="reviews"]/li')
    for rev in revs:
        if rev.xpath('.//span[@class="reviewIsTranslation"]'):
            continue

        review = Review()
        review.type = 'user'
        review.url = data.response_url
        review.ssid = rev.xpath('.//div[@class="wrap-loader"]/@id').string().split('-')[-1]

        date = rev.xpath('.//span[@class="review-date"]/@title').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//div/span[contains(@title, "profile")]/text()').string() or rev.xpath('.//div[@class="reviewHeader-left"]/span[contains(@title, "membre de ")]/text()').string()
        if author:
            author = remove_emoji(serialize_text(author)).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        hlp_yes = rev.xpath('.//span[contains(@class, "like-button")]/text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[contains(@class, "dislike-button")]/text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev.xpath('.//div[@class="reviewRating"]//div/@aria-label').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(': ')[-1].split('/')[0])
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        title = rev.xpath('.//h2[@class="reviewTitle"]//span/text()').string()
        excerpt = rev.xpath('.//div[@class="review-long-content"]//text()').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('.//div[contains(@class, "main-text")]//text()').string(multiple=True)

        if excerpt and len(remove_emoji(serialize_text(excerpt)).strip()) > 2:
            if title:
                review.title = remove_emoji(serialize_text(title)).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(serialize_text(excerpt)).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, context)

    elif product.reviews:
        session.emit(product)


def process_pro_review(data, context, session):
    strip_namespace(data)

    product = context['product']

    review = Review()
    review.type = 'pro'
    review.url = data.response_url
    review.ssid = product.ssid

    title = data.xpath('//span[@class="articleTitle" or @class="articleEditorialTitle"]/text()').string()
    if title:
        review.title = remove_emoji(serialize_text(title)).strip()

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="article-author"]/span/text()').string()
    if author:
        author = remove_emoji(serialize_text(author)).strip()
        if author:
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="mark"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[@class="plus"]/li/text()').strings()
    if not pros:
        pros = data.xpath('//p[contains(text(), "Les Plus")]/following-sibling::p[1][starts-with(normalize-space(.), "+")]//text()').strings()

    for pro in pros:
        pro = remove_emoji(serialize_text(pro)).strip(' ….+-–')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="minus"]/li/text()').strings()
    if not cons:
        cons = data.xpath('//p[contains(text(), "Les moins")]/following-sibling::p[1][starts-with(normalize-space(.), "-") or starts-with(normalize-space(.), "–")]//text()').strings()

    for con in cons:
        con = remove_emoji(serialize_text(con)).strip(' ….+-–')
        if con:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="content-header"]//text()').string(multiple=True)
    if summary:
        summary = re.sub(r'<.*?>', '', (remove_emoji(serialize_text(summary)).strip()))
        if summary:
            review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(@id, "conclusion")]/following-sibling::p[not(regexp:test(., "Les Plus|Les moins") or starts-with(normalize-space(.), "+") or starts-with(normalize-space(.), "-") or starts-with(normalize-space(.), "–"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = re.sub(r'<.*?>', '', (remove_emoji(serialize_text(conclusion)).strip()))
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="t-content"]/p[not(preceding-sibling::h2[contains(@id, "conclusion")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<.*?>', '', (remove_emoji(serialize_text(excerpt)).strip()))
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
