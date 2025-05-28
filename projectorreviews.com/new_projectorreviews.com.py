from agent import *
from models.products import *


# Prune gets stuck on these pages and doesn't continue parsing
XPROD = ['https://www.projectorreviews.com/epson/epsons-laser-projectors-transforming-the-world-we-know-in-entertainment-venues-and-other-large-scale-environments-2/']


def run(context, session):
    session.queue(Request('https://www.projectorreviews.com/projector-categories/', use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//h3[contains(@class, "title")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use="curl", force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if url not in XPROD:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_review, dict(context, title=title, url=url))

# no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review of ')[0].split(' Review -')[0].split(' Review: ')[0].replace('A First Look Review', '').replace('Projector Review', '').replace('PROJECTOR REVIEW', '').replace(' Review', '').replace(' REVIEW', '').strip(' –-')
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat'].replace('Review of', '').replace('Reviews of', '').replace('Reviews', '').strip()

    product.url = data.xpath('//a[img[regexp:test(@alt, "Buy Now|buy-now", "i")]]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[contains(text(), "Posted on ")]/span[contains(., ",")]/text()').string()

    author = data.xpath('//div[contains(text(), "Posted on ")]/span[not(contains(., ","))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//div[(div[contains(@class, "star-rating")] and div[contains(@id, "text")]) or (h3 and div/div[contains(@class, "star-rating")])]')
    for grade in grades:
        grade_name = grade.xpath('(div[contains(@id, "text")]|h3)/text()').string()
        grade_val = grade.xpath('count(.//div[contains(@class, "star-rating")])')
        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name.title(), value=grade_val, best=6.0))

    pros = data.xpath('//div[div[contains(text(), "Pros")]]//p|((//p|//h3)[contains(., "PROS")]/following-sibling::ul)[1]/li')
    if pros:
        pros = set(pro.xpath('.//text()').string(multiple=True).strip(' +-*.;') for pro in pros if pro.xpath('.//text()').string(multiple=True))

    for pro in pros:
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div[contains(text(), "Cons")]]//p|((//p|//h3)[contains(., "CONS")]/following-sibling::ul)[1]/li')
    if pros:
        cons = set(con.xpath('.//text()').string(multiple=True).strip(' +-*.;') for con in cons if con.xpath('.//text()').string(multiple=True))

    for con in cons:
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[regexp:test(text(), "Final Thoughts|CONCLUSION")]/following::p[not(regexp:test(normalize-space(text()), "^\+|^\-") or @style or strong[regexp:test(text(), "pros|cons", "i")])]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('�', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[not(regexp:test(normalize-space(text()), "^\+|^\-") or @style or strong[regexp:test(text(), "pros|cons", "i")] or preceding::h3[regexp:test(text(), "Final Thoughts|CONCLUSION")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('�', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
