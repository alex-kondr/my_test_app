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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cnetfrance.fr/produits/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "col-xxs-1")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'qui est le meilleur|Meilleur', title, flags=re.I):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test : ', '').replace('Test ', '').split(': ')[0].replace('On a testé le ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.htm', '')
    product.category = context['cat'].replace(' / ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time[@datetime]/text()').string()
    if date:
        review.date = date.split(' le', 1)[-1].split(' à ')[0].strip()

    author = data.xpath('//meta[@property="nrbi:authors"]/@content[not(contains(., "CNET France"))]').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating"]//span/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    if not grade_overall:
        grade = data.xpath('//div[h1]//div[contains(@class, "rtg__inr")]/@class').string()
        if grade:
            grade_overall = re.search(r'\d+', grade)
            if grade_overall:
                grade_overall = float(grade_overall.group())
                if 'half' in grade:
                    grade_overall += .5

                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[h2[contains(text(), "Les plus")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[h2[contains(text(), "Les plus")]]/text()[normalize-space(.)]').string(multiple=True)
        if pros:
            pros = pros.strip(' +-*.:;•–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

    cons = data.xpath('//div[h2[contains(text(), "Les moins")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[h2[contains(text(), "Les moins")]]/text()[normalize-space(.)]').string(multiple=True)
        if cons:
            cons = cons.strip(' +-*.:;•–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

    summary = data.xpath('//main[@id="content"]/article/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(text(), "Notre")]/following-sibling::p[not(.//img)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(text(), "Notre")]/preceding-sibling::p[not(.//img)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(.//img)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
