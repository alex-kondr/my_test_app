from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.tomshw.it/notizie-hardware-type/recensione/', use="curl"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='news_items_column']/div[contains(@class, 'news_item')]")
    for rev in revs:
        name = rev.xpath(".//div[@class='title']/a/text()").string()
        url = rev.xpath(".//div[@class='title']/a/@href").string()
        cat = rev.xpath(".//div[@class='shout']/text()").string()
        session.queue(Request(url, use="curl"), process_review, dict(name=name, url=url, cat=cat))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl"), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context["name"].split('|')[0].split("– Recensione")[0].split("Recensione ")[-1].split("Test ")[-1].split(',')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.url = context['url']
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context["name"]
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath("//meta[@property='article:modified_time']/@content").string()
    if date:
        date = date.split('T')[0]
    else:
        date = data.xpath("//time[@class='item_short_desc_time']/following::text()[1]").string()
        if date:
            date = date.split(' ', 1)[-1].rsplit(' ', 1)[0]
    if date:
        review.date = date

    author = data.xpath("//div[@class='article_author_name']/strong").first()
    if author:
        name = author.xpath(".//text()").string(multiple=True)
        url = author.xpath("a/@href").string()
        if url:
            ssid = url.split('/')[-2]
            review.authors.append(Person(name=name, ssid=ssid, profile_url=url))
        else:
            review.authors.append(Person(name=name, ssid=name))

    grade_overall = len(data.xpath("//div[@class='full-stars']/i"))
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5))

    pros = data.xpath("//h4[text()='Pro']/following-sibling::ul/li/text()")
    if pros:
        if len(pros) == 1:
            pros = pros.string().split(';')
        else:
            pros = pros.strings()
        for pro in pros:
            pro = pro.replace(';', '').replace('.', '').strip()
            if pro:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//h4[text()='Contro']/following-sibling::ul/li/text()")
    if cons:
        if len(cons) == 1:
            cons = cons.string().split(';')
        else:
            cons = cons.strings()
        for con in cons:
            con = con.replace(';', '').replace('.', '').strip()
            if con:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//div[@class='generic_main_article']/div/p[1]//text()").string(multiple=True)
    if not summary:
        summary = data.xpath("//div[@class='generic_main_article']/following::body/p[1]//text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//div[@class='generic_main_article']/div/*[regexp:test(local-name(), '^h\d')][regexp:test(., 'conclusioni|verdetto', 'i')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='generic_main_article']/following::body/*[regexp:test(local-name(), '^h\d')][regexp:test(., 'conclusioni|verdetto', 'i')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='generic_main_article']/div/p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='generic_main_article']/following::body/p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary.strip(), '')
        if conclusion:
            excerpt = excerpt.replace(conclusion.strip(), '')
        excerpt = excerpt.split("»")[0].strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
