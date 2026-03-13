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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://press-start.com.au/category/reviews/', max_age=0), process_catlist, {})


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="options"]/li/a[@class="block-subcat"]')
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath("text()").string()

        if url and name:
            name = name.replace(' Reviews', '').strip()
            if name not in ['Movie', 'Tech']:
                name = "Games|" + name

            session.queue(Request(url, max_age=0), process_category, dict(context, cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    revs = data.xpath("//div[@data-id=0]//h3[@class='title']/a")
    for rev in revs:
        url = rev.xpath("@href").string()
        title = rev.xpath("./text()").string()
        if url and title:
            session.queue(Request(url, max_age=0), process_review, dict(context, url=url, title=title))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_category, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review')[0]
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//head/title/text()').string() or context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath('//a[@rel="author"]/@href[not(contains(., "/author/admin/"))]').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, profile_url=author_url, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score__wrap lr-all-c"]/div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath("//div[@class='cb-pros-cons cb-pro']")
    if not pros:
        pros = data.xpath("//p[contains(., 'Pros')]/following-sibling::ul[1]/li")
    if not pros:
        pros = data.xpath("//div[@class='lets-review-block__procon lets-review-block__pro']")

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@class='cb-pros-cons cb-con']")
    if not cons:
        cons = data.xpath("//p[contains(., 'Cons')]/following-sibling::ul[1]/li//text()")
    if not cons:
        cons = data.xpath("//div[@class='lets-review-block__procon lets-review-block__con']//text()")

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "title")]/p[contains(@class, "subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]//parent::p//following-sibling::p//text()").string(multiple=True)
    if not(conclusion):
        conclusion = data.xpath("//img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]//following-sibling::text()").string(multiple=True)
    if not(conclusion):
        conclusion = data.xpath("descendant::div[@itemprop='reviewBody']//text()").string(multiple=True)
    if not(conclusion):
        conclusion = data.xpath("descendant::div[regexp:test(@class,'entry-content')]/p[preceding-sibling::node()[regexp:test(normalize-space(.),'Conclusion','i')]]//text()").string(multiple=True)
    if not(conclusion):
        conclusion = data.xpath("//div[@class='lets-review-block lets-review-block__conclusion__wrap lets-review-block__pad']/div[@class='lets-review-block__conclusion']//text()").string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[regexp:test(@class,'entry-content')]/p[following-sibling::node()[regexp:test(normalize-space(.),'Conclusion','i')]]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[regexp:test(@class,'entry-content')]/p[following-sibling::div[@data-pid]]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[regexp:test(@class,'entry-content')]/p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("(//article/div[@class='entry-content-wrap clearfix']//img/@src[contains(., 'CONCLUSION')])[1]/parent::img/parent::p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("(//article//div/div/p[last()])[1]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[regexp:test(@class,'single-content')]//section[@class='cb-entry-content clearfix']//p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//article[contains(@class, 'entry-content clearfix')]//p//text()").string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
