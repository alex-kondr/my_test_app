from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.pcmasters.de/testbericht.html', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Test - ')[0].split(' im Test')[0].split(' Test der ')[0].split(' auf moderner ')[0].split(' Test & Vergleich')[0].split(' Test/Review')[0].split('Chair/Review')[0].split('Platinum/Review')[0].split(' im Vergleich')[0].split(' Analyse der ')[0].split(' im Langzeit-Test:')[0].split(' im Dauer-Test')[0].split(' und Reviews')[0].split(' Test ')[0].split(' Test: ')[0].replace(' Testbericht', '').replace(' im Schnelltest', '').replace(' im Kurztest', '').replace(' Schnelltest', '').replace(' (Testbericht)', '').replace(' im Multiplayer-Test', '').replace(' im Langzeittest', '').replace('Kurztest:', '').replace(' Kurztest', '').replace('Review: ', '').replace(' im Überblick', '').replace(' Test', '').replace(' Review', '').strip(' :')
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]

    product.category = data.xpath('//span[@class="cat-label" and not(contains(., "Testbericht"))][last()]//text()').string()
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@itemprop="author"]/a//text()').string(multiple=True)
    author_url = data.xpath('//span[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="rating"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', ''))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    grades = data.xpath('//div[@class="ratingitem"]')
    for grade in grades:
        grade_name = grade.xpath('div[@class="itemname"]/text()').string()
        grade_val = grade.xpath('.//div[@class="progress-bar"]/text()').string()

        if grade_name and grade_val:
            grade_val = float(grade_val.replace('%', ''))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=100.0))

    pros = data.xpath('((//h2|//h3)[@id="pro" or normalize-space(text())="Pro"]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('((//h2|//h3)[@id="contra" or normalize-space(text())="Contra"]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//body/p/strong//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(@id, "fazit") or contains(text(), "Fazit")]/following-sibling::p[not(preceding::h3[contains(text(), "Preise und Marktverfügbarkeit")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="shortconclusion"]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@class="articleBody"]|//div[@class="articleBody"]/div)/p[not(preceding::h2[contains(@id, "fazit") or contains(text(), "Fazit")] or preceding::h3[contains(text(), "Preise und Marktverfügbarkeit")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
