from agent import *
from models.products import *
import simplejson
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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.weleda.de/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "product-category")]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-teaser__content"]')
    for prod in prods:
        name = prod.xpath('a/h2/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Weleda'

    revs_url = 'https://api.bazaarvoice.com/data/reviews.json?resource=reviews&action=REVIEWS_N_STATS&filter=productid:eq:{ssid}&filter=contentlocale:eq:en*,fr*,de*,de_DE,de_DE&filter=isratingsonly:eq:false&filter_reviews=contentlocale:eq:en*,fr*,de*,de_DE,de_DE&include=authors,products,comments&filteredstats=reviews&Stats=Reviews&incentivizedstats=true&limit=30&offset=0&limit_comments=3&sort=relevancy:a1&passkey=caWgJC0tY4TIafxWjxSYmT9eZByIN5zv7vBtMRUx9wt50&apiversion=5.5&displaycode=17699-de_de'.format(ssid=product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('Results', [])
    for rev in revs:
        if rev.get('IsSyndicated'):
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('Id'))

        date = rev.get('SubmissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('UserNickname')
        author_ssid = rev.get('AuthorId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('Rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('Pros', [])
        if isinstance(pros, list):
            for pro in pros:
                review.add_property(type='pros', value=pro)

        cons = rev.get('Cons', [])
        if isinstance(cons, list):
            for con in cons:
                review.add_property(type='cons', value=con)

        hlp_yes = rev.get('TotalPositiveFeedbackCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('TotalNegativeFeedbackCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_recommended = rev.get('IsRecommended')
        if is_recommended is True:
            review.add_property(type='is_recommended', value=True)

        title = rev.get('Title')
        excerpt = rev.get('ReviewText')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('\t', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt and '(Ursprünglich erschienen auf influenster.com)' not in excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('\t', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('TotalResults', 0))
    offset = context.get('offset', 0) + 30
    if offset < revs_cnt:
        revs_url = 'https://api.bazaarvoice.com/data/reviews.json?resource=reviews&action=REVIEWS_N_STATS&filter=productid:eq:{ssid}&filter=contentlocale:eq:en*,fr*,de*,de_DE,de_DE&filter=isratingsonly:eq:false&filter_reviews=contentlocale:eq:en*,fr*,de*,de_DE,de_DE&include=authors,products,comments&filteredstats=reviews&Stats=Reviews&incentivizedstats=true&limit=30&offset={offset}&limit_comments=3&sort=relevancy:a1&passkey=caWgJC0tY4TIafxWjxSYmT9eZByIN5zv7vBtMRUx9wt50&apiversion=5.5&displaycode=17699-de_de'.format(ssid=product.ssid, offset=offset)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt, offset=offset))

    elif product.reviews:
        session.emit(product)
