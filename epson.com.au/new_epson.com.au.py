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


def RequestRevs(mpn, offset):
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: gzip, deflate' -H 'Referer: https://www.epson.com.au/' -H 'bv-bfd-token: 5625,main_site,en_AU' -H 'Origin: https://www.epson.com.au' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site'"""
    url = 'https://apps.bazaarvoice.com/bfd/v1/clients/Epson-EN_AU/api-products/cv2/resources/data/reviews.json?resource=reviews&action=REVIEWS_N_STATS&filter=productid%3Aeq%3A' + mpn + '&filter=contentlocale%3Aeq%3Aen_AU%2Cen_AU&filter=isratingsonly%3Aeq%3Afalse&filter_reviews=contentlocale%3Aeq%3Aen_AU%2Cen_AU&include=authors%2Cproducts%2Ccomments&filteredstats=reviews&Stats=Reviews&limit=30&offset=' + str(offset) + '&limit_comments=3&sort=submissiontime%3Adesc&apiversion=5.5&displaycode=5625-en_au'
    r = Request(url, use='curl', force_charset='utf-8', options=options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.epson.com.au/shoponline/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//section[@id="products"]//div[@class="card-block"]')
    for cat in cats:
        name = cat.xpath('h3/text()').string()
        url = cat.xpath('a/@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods_json = data.xpath('//script[contains(., "const products = ")]/text()').string()
    try:
        prods = simplejson.loads(prods_json.split('const products = ')[-1].strip(' ;'))
    except:
        prods = []

    for prod in prods:
        if prod.get('Status') == 'invisible':
            continue

        product = Product ()
        product.name = prod.get('Name')
        product.ssid = prod.get('ID')
        product.sku = prod.get('ProductID')
        product.url = 'https://www.epson.com.au/finder.asp?id=' + product.sku
        product.category = context['cat']
        product.manufacturer = 'Epson'

        mpn = prod.get('Globalcode')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        revs_cnt = prod.get('TotalReviews')
        if revs_cnt and int(revs_cnt) > 0:
            session.do(RequestRevs(mpn, 0), process_reviews, dict(product=product, mpn=mpn))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content).get('response', {})
    except:
        revs_json = {}

    revs = revs_json.get('Results', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('Id')

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

        grades = rev.get('SecondaryRatings')
        for grade in grades.values():
            grade_name = grade.get('Id')
            grade_val = grade.get('Value')
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        is_recommended = rev.get('IsRecommended')
        if is_recommended is True:
            review.add_property(type='is_recommended', value=True)

        title = rev.get('Title')
        excerpt = rev.get('ReviewText')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('TotalResults', 0))
    offset = context.get('offset', 0) + 30
    if offset < revs_cnt:
        session.do(RequestRevs(context['mpn'], offset), process_reviews, dict(context, product=product, offset=offset, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
