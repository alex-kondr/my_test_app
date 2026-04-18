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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('http://press-start.com.au/category/reviews/', use='curl'), process_catlist, {})


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="options"]/li/a[@class="block-subcat"]')
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath("text()").string()

        if url and name:
            session.queue(Request(url, use='curl'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    revs = data.xpath("//div[@data-id=0]//h3[@class='title']/a")
    for rev in revs:
        url = rev.xpath("@href").string()
        title = rev.xpath("./text()").string()

        if url and title:
            session.queue(Request(url, use='curl'), process_review, dict(context, url=url, title=title))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_category, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review')[0].replace('Review: ', '').replace('REVIEW: ', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(., "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = context['cat'].replace(' Reviews', '').strip()
    if category not in ['Movie', 'Tech']:
        category = "Games|" + category

    product.category = category

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//head/title/text()').string() or context['title']
    review.url = context['url']
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

    grades = data.xpath('//div[contains(@class, "block__crit") and @data-score]')
    for grade in grades:
        grade_name = grade.xpath('div[contains(@class, "title")]/text()').string()
        grade_val = grade.xpath('div[contains(@class, "score")]/text()').string()
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

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
        cons = data.xpath("//p[contains(., 'Cons')]/following-sibling::ul[1]/li")
    if not cons:
        cons = data.xpath("//div[@class='lets-review-block__procon lets-review-block__con']")

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "title")]/p[contains(@class, "subtitle")]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//p[img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]//following-sibling::text()|//img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]/following-sibling::em//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("descendant::div[@itemprop='reviewBody']//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='lets-review-block lets-review-block__conclusion__wrap lets-review-block__pad']/div[@class='lets-review-block__conclusion']//text()").string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]/preceding-sibling::text()|//p[img[contains(@src, 'CONCLUSION') or contains(@src, 'Conclusion') or contains(@src, 'conclusion')]]/preceding-sibling::p[not(contains(@class, 'post-intro-line'))]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[regexp:test(@class,'entry-content')]/p[following-sibling::div[@data-pid]]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[contains(@class,'entry-content')]/p[not(@class)]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("(//article/div[@class='entry-content-wrap clearfix']//img/@src[contains(., 'CONCLUSION')])[1]/parent::img/parent::p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("(//article//div/div/p[last()])[1]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[regexp:test(@class,'single-content')]//section[@class='cb-entry-content clearfix']//p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//article[contains(@class, 'entry-content clearfix')]//p//text()").string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
