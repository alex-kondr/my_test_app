from agent import *
from models.products import *
import re
import HTMLParser


h = HTMLParser.HTMLParser()
XCAT = ['Beste games']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://gamer.nl/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(., "Reviews")]/nav/ul/li[contains(@class, "group/category")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[.//p[contains(@class, "font-bold")]]')
    for rev in revs:
        title = rev.xpath('.//p/text()').string().replace(' &amp;', '')
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(., "Volgende")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('Review: ')[-1].replace('Review -', '').replace('Review-in-progress: ', '').replace(' &amp;', '').strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p[contains(@class, "extra-info text-white")]/text()').string()
    if date:
        review.date = date.split(' - ')[0]

    author = data.xpath('//span[contains(., "Door:") and not(preceding::span[contains(., "Volgende artikel")])]/a[contains(@href, "/auteur/")]/text()').string()
    author_url = data.xpath('//span[contains(., "Door:") and not(preceding::span[contains(., "Volgende artikel")])]/a[contains(@href, "/auteur/")]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('(//div[div/span[contains(., "Conclusie")]])[1]//div[contains(@class, "text-center")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.').replace(' ', ''))
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//li[*[contains(@class, "success")]]')
    for pro in pros:
        pros_ = pro.xpath('.//text()').string(multiple=True).split('- ')
        for pro_ in pros_:
            pro_ = h.unescape(pro_).strip(' +-*.')
            if pro_:
                review.add_property(type='pros', value=pro_)

    cons = data.xpath('//li[*[contains(@class, "destructive")]]')
    for con in cons:
        cons_ = con.xpath('.//text()').string(multiple=True).split('- ')
        for con_ in cons_:
            con_ = h.unescape(con_).strip(' +-*.')
            if con_:
                review.add_property(type='cons', value=con_)

    summary = data.xpath('//h2[contains(@class, "text-white italic") and not(preceding::span[contains(., "Volgende artikel")])]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//p[@class="intro-line" and not(preceding::span[contains(., "Volgende artikel")])]//text()').string(multiple=True)

    if summary:
        summary = h.unescape(summary)
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Conclusie|Concluderend")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[div/span[contains(., "Conclusie")]]//p//text()').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusie|Concluderend")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[h2]/p[not(@class="intro-line")]//text()').string(multiple=True)

    if excerpt:
        excerpt = re.sub(r'href=\S+', '', h.unescape(excerpt))
        excerpt = re.sub(r'rel=\"\S+\s?\S+\"', '', excerpt)
        excerpt = re.sub(r'target=\"\S+\s?\S+\"', '', excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
