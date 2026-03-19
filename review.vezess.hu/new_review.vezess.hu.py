from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.vezess.hu/ujauto-teszt/", max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[contains(@class, 'm-list__item')]")
    for rev in revs:
        title = rev.xpath(".//a[@class='m-list__titleLink']/@title").string()
        url = rev.xpath(".//a[@class='m-list__titleLink']/@href").string()
        ssid = rev.xpath("@post_id").string()
        session.queue(Request(url, max_age=0), process_review, dict(context, title=title, url=url, ssid=ssid))

    next_url = data.xpath("//a[@class='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.ssid = str(context["ssid"])
    product.url = context["url"]
    product.category = "Cars"

    try:
        rev_json = simplejson.loads(data.xpath("//script[contains(., 'itemReviewed')]/text()").string()).get("itemReviewed", {})

        product.name = rev_json.get("name", '').strip()
        product.manufacturer = rev_json.get("brand", {}).get('name')

        cat = rev_json.get("category")
        if cat:
            product.category += "|" + cat
    except:
        pass

    if not product.name:
        product.name = data.xpath("//h1[contains(@class,'o-post__title')]/text()").string()
    if not product.name:
        product.name = data.xpath("//h1[contains(@class, 'title')]/text()").string()
    if not product.name:
        product.name = context['title']

    product.name = product.name.split('Teszt:')[-1].split('–')[0].split('Vezettük: ')[-1].strip()

    review = Review()
    review.type = "pro"
    review.title = context["title"]
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@class, 'm-author__authorName')]").first()
    if author:
        author_name = author.xpath("text()").string()
        author_url = author.xpath("@href").string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    grade_overall = data.xpath('count(//i[@class="fas fa-star"]) + count(//i[@class="fas fa-star-half-alt"]) div 2')
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath("//td[@class='pros']//li")
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//td[@class='cons']//li")
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//p[contains(@class,'o-post__lead lead')]/text()").string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//h2[@id='ertekeles']/following-sibling::div/p/text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class,"article-body")]//p[not(contains(@id, "caption-attachment"))][not(.//img or preceding::h2[@id="ertekeles"])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class,"article-body")]//div[@class="paragraph"][not(.//h2)][not(.//table)][not(.//img or preceding::h2[@id="ertekeles"])]//text() | //div[@class="paragraph"]//p[not(contains(@id, "caption-attachment") or preceding::h2[@id="ertekeles"])]//text()').string(multiple=True)

    if excerpt:
        excerpt= excerpt.replace(u'\uFEFF', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, "").strip()

        if summary:
            excerpt = excerpt.replace(summary, "").strip()

        if len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

            session.emit(product)
