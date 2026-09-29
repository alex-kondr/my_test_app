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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://androidworld.nl/reviews/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[@data-name="post"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//h1[@data-name="title"]/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Technologie'

    product.name = data.xpath('//h3[contains(@class, "leading-snug")]/text()').string()
    if not product.name:
        product.name = title.replace('Mini-review:', '').replace('Mini-review ', '').split('-review:')[0].split('review:')[0].split(': mid-ranger doet veel')[0].split(': meer klasse')[0].split(': tweede toptoestel')[0].split(': flinke accu')[0].split(': smartphone met')[0].split(': smartwatch voor')[0].split(': minder sprekend')[0].split(': terugkeer van')[0].split(': 24 uur met')[0].split(': herkenbare smartphone')[0].split(': wie niet')[0].split(': sterke comeback')[0].split(': verfijning van')[0].split(': en de laatste')[0].split(': met stip op')[0].split(': stijlvolle metalen')[0].split(': topsmartphones')[0].split(': de nieuwe ')[0].split(': verrassende ')[0].split(': (g)een grote')[0].split(': nieuwe LG')[0].split(': budget en')[0].split(': chique uitstraling')[0].split(': waar voor')[0].replace('reviews op Androidworld', '').replace(' videoreview', '').replace('Review:', '').replace('Preview nieuwe ', '').replace('Preview ', '').replace('Cameratest:', '').replace('(videoreview)', '').replace(' getest', '').replace('[video]', '').replace('Review ', '').replace(' review', '').split('PureView eerste')[0].split('preview van de')[0].split(": 'laatste kans'")[0].replace('Videoreview ', '').split(' review - ')[0].split(' review – ')[0].strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(a/@href, "/auteur/") or contains(a/@href, "/community/")]/div/div[not(@class)]/text()[contains(., ", ")]').string()
    if date:
        review.date = date.split(', ')[0]

    author = data.xpath('//div[contains(a/@href, "/auteur/") or contains(a/@href, "/community/") and div/div[not(@class)]/text()[contains(., ", ")]]/a//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(a/@href, "/auteur/") or contains(a/@href, "/community/") and div/div[not(@class)]/text()[contains(., ", ")]]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@data-name="rating-large"]/div/div[@class="font-bold"]/text()').string(multiple=True)
    if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//div[@class="pros-cons-list"])[1]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[@class="pros-cons-list"])[2]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[not(preceding::h3[contains(@class, "leading-snug")])]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).replace(u'Ã¡', u'á').replace(u"Ã\xa0", u"à").replace(u"Ã ", u"à").replace(u"Ã¢", u"â").replace(u"Ã©", u"â").replace(u'Ã¯', u'ï').replace(u'Ã¨', u'è').replace(u'Ã¤', u'ä').replace(r"Å\ufffd", u'ō').replace(r'Å\uFFFD', u'ō').replace(u'Ã¼', u'ü').replace(u'â€�', u"'").replace(u'Ã±', u'ñ').replace(u'â€¦', u'…').replace(u'Ãª', u'ê').replace(u'Ã§', u'ç').replace(u'â€™', "'").replace(u'â€˜', "'").replace(u'Ã¶', u'ö').replace(u'Ã«', u'ë').replace(u'â€œ', '“').replace(u"â€\x9D", "”").replace(u"â€", "”").replace(u'Âµ', u'µ').replace(u"Â°", u"°").replace(u"Ã³", u"ó").replace(u'Â´', u"'").replace(u"Â¨", " ").replace(u"Â´e", "é").replace(u"Â´", "")
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//article[@data-name="content"]/p[not(preceding::*[contains(self::h3/@class, "leading-snug") or contains(self::h2, "Conclusie")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).replace(u'Ã¡', u'á').replace(u"Ã\xa0", u"à").replace(u"Ã ", u"à").replace(u"Ã¢", u"â").replace(u"Ã©", u"â").replace(u'Ã¯', u'ï').replace(u'Ã¨', u'è').replace(u'Ã¤', u'ä').replace(r"Å\ufffd", u'ō').replace(r'Å\uFFFD', u'ō').replace(u'Ã¼', u'ü').replace(u'â€�', u"'").replace(u'Ã±', u'ñ').replace(u'â€¦', u'…').replace(u'Ãª', u'ê').replace(u'Ã§', u'ç').replace(u'â€™', "'").replace(u'â€˜', "'").replace(u'Ã¶', u'ö').replace(u'Ã«', u'ë').replace(u'â€œ', '“').replace(u"â€\x9D", "”").replace(u"â€", "”").replace(u'Âµ', u'µ').replace(u"Â°", u"°").replace(u"Ã³", u"ó").replace(u'Â´', u"'").replace(u"Â¨", " ").replace(u"Â´e", "é").replace(u"Â´", "")
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
