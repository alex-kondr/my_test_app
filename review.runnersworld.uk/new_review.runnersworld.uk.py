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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.runnersworld.com/uk/gear/shoes/', use='curl', max_age=0), process_category, dict(cat='Shoes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/clothes/', use='curl', max_age=0), process_category, dict(cat='Clothes'))
    session.queue(Request('https://www.runnersworld.com/uk/gear/tech/', use='curl', max_age=0), process_category, dict(cat='Tech'))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    data_json = data.xpath('''//script[contains(., '"contentId":"')]/text()''').string()
    if data_json:
        cat_id = simplejson.loads(data_json).get('metadata', {}).get('contentId')
        next_url = 'https://www.runnersworld.com/uk/api/feed-content/?id={}&type=subsection&limit=12&token=2&offset=1&params=%7B%22isHomePage%22%3Afalse%2C%22contentSectionEnabled%22%3Atrue%7D'.format(cat_id)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, cat_id=cat_id))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = simplejson.loads(data.content).get('data', {}).get('feedContent')
    if not revs:
        return

    for rev in revs:
        ssid = str(rev.get('display_id'))
        title = rev.get('metadata', {}).get('short_title')
        url = 'https://www.runnersworld.com/uk/a' + str(ssid)

        if not re.search(r'[Tt]he \d* ?best', title) and 'review' in title.lower():
            session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, ssid=ssid, url=url))

    offset = context.get('offset', 1) + 12
    next_url = 'https://www.runnersworld.com/uk/api/feed-content/?id={id}&type=subsection&limit=12&token=2&offset={offset}&params=%7B%22isHomePage%22%3Afalse%2C%22contentSectionEnabled%22%3Atrue%7D'.format(id=context['cat_id'], offset=offset)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, offset=offset))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.ssid = str(context['ssid'])
    product.category = context['cat']

    product.name = data.xpath('//h2[contains(@data-theme-key, "product-title")]/text()').string()
    if not product.name:
        product.name = context['title'].replace('Review:', '').replace(' Review', '').split(': ')[0].replace(', reviewed', '').replace(' review', '').strip()

    product.url = data.xpath('//a[contains(., "at Amazon")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@class, "product-link")]/@href').string()
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

    pros = data.xpath('//div[contains(h3, "Pros")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h3, "Cons")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//header//div[h1]//p//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary)
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Who should buy|verdict", "i")]/following::p//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Who should buy|verdict", "i")]/preceding::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('''//div[contains(@class, "body")]/p[not(preceding::div[contains(., "What everyone's reading")] or a[@data-vars-ga-product-primary-ux="button"])]//text()''').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).replace('RW Verdict:', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)