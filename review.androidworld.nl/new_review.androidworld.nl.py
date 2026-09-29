from agent import *
from models.products import *


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
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

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
        product.name = context['title'].replace('Mini-review:', '').replace('Mini-review ', '').split('-review:')[0].split('review:')[0].split(': mid-ranger doet veel')[0].split(': meer klasse')[0].split(': tweede toptoestel')[0].split(': flinke accu')[0].split(': smartphone met')[0].split(': smartwatch voor')[0].split(': minder sprekend')[0].split(': terugkeer van')[0].split(': 24 uur met')[0].split(': herkenbare smartphone')[0].split(': wie niet')[0].split(': sterke comeback')[0].split(': verfijning van')[0].split(': en de laatste')[0].split(': met stip op')[0].split(': stijlvolle metalen')[0].split(': topsmartphones')[0].split(': de nieuwe ')[0].split(': verrassende ')[0].split(': (g)een grote')[0].split(': nieuwe LG')[0].split(': budget en')[0].split(': chique uitstraling')[0].split(': waar voor')[0].replace('reviews op Androidworld', '').replace(' videoreview', '').replace('Review:', '').replace('Preview nieuwe ', '').replace('Preview ', '').replace('Cameratest:', '').replace('(videoreview)', '').replace(' getest', '').replace('[video]', '').replace('Review ', '').replace(' review', '').split('PureView eerste')[0].split('preview van de')[0].split(": 'laatste kans'")[0].replace('Videoreview ', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(a/@href, "/auteur/")]/div/div[not(@class)]/text()').string()
    if date:
        review.date = date.split(', ')[0]

    # author = data.xpath('/text()').string()
    # author_url = data.xpath('/@href').string()
    # if author and author_url:
    #     author_ssid = author_url.split('/')[-1]
    #     review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    # elif author:
    #     review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h3[contains(text(), "Summary")]]/div//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
