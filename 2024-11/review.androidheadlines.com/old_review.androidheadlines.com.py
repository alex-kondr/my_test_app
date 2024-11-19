from agent import *
from models.products import *
import re


CLEANR = re.compile('<.*?>')


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.androidheadlines.com/category/reviews"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="post-title post-thumbnail-title"]')
    for rev in revs:
        title = rev.xpath('.//a[@class="post-url"]/text()').string()
        url = rev.xpath('.//a[@class="post-url"]/@href').string()
        grade_overall = rev.xpath('parent::body/preceding-sibling::head[1]//@fill[contains(., "#FFAF13")]')
        if grade_overall:
            grade_overall = len(grade_overall)

        session.queue(Request(url), process_review, dict(context, title=title, url=url, grade_overall=grade_overall))

    next_url = data.xpath("//a[@class='next page-link']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):

    # there are some pages that doesn't contain product
    if data.xpath("//div[@class='deal_list']"):
        return

    if re.search("Top \d+", context['title']) or 'Best ' in context['title'] or 'The best ' in context['title']:
        process_reviews(data, context, session)
        return

    product = Product()

    product.name = context['title'].split("Featured: ")[-1].split("Featured Review: ")[-1].split("Case of the Day: ")[-1].split(' Review -')[0].split(' Review –')[0].replace('Review Video', '').replace("Android Game App Review", '').replace(", Android App Review", '')
    if product.name.lower().split()[0] == 'review:':
        product.name = product.name.split(':', 1)[-1]
    elif 'review:' in product.name.lower():
        product.name = product.name.split('review:')[0].split('Review:')[0].split('REVIEW:')[0]
    product.name = product.name.replace('review', '').replace('Review', '').replace('REVIEW', '')

    url = data.xpath('//a[regexp:test(., "buy", "i")]/@href').string()
    if not url:
        url = data.xpath('//a[contains(@rel, "sponsored")][@class="btn btn-primary"]/@href').string()
    if url:
        product.url = url
    else:
        product.url = context['url']

    product.ssid = context['url'].split('/')[-1].replace('.html', '')

    cats_list = data.xpath("//a[@class='taxonomy category']//text()")
    cats = ''
    for cat in cats_list:
        cats += cat.string().replace("News", "").replace('Reviews', '').strip() + "|"
    cats = cats.strip('| ')
    if not cats:
        cats = 'Tech'
    product.category = cats

    review = Review()
    review.title = context["title"]
    review.ssid = product.ssid
    review.url = context['url']
    review.type = "pro"

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    grade_overall = context.get('grade_overall')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    authors = data.xpath("//div[@class='entry-meta-author-name']//a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    pros = data.xpath("//span[contains(.,'Pros')]/following-sibling::ul//text()").strings()
    if not pros:
        pros = data.xpath("//p[contains(.,'Pro:')]/following-sibling::ul[not(preceding-sibling::p[contains(.,'Cons:')])]//text()").strings()
    if not pros:
        pros = data.xpath("//p[contains(., 'Pro')]/following-sibling::ul//li//text()").strings()
    if not pros:
        pros = data.xpath("//p[contains(.,'Pros:')]/following-sibling::*[not(preceding-sibling::*[contains(.,'Cons:')])]/text()").strings()
    if not pros:
        pros = data.xpath("//*[text()='Pros']/following-sibling::*//ul/li/text()").strings()
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "The Good")]]/following-sibling::p[following-sibling::p[.//strong[contains(., "The Bad")]]]//text()').strings()
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "The Good")]]//text()[not(contains(., "The Good"))]').strings()
    for pro in pros:
        if pro.lower() != "pro":
            review.add_property(type='pros', value=pro)

    cons = data.xpath("//span[contains(.,'Cons')]/following-sibling::ul//text()").strings()
    if not cons:
        cons = data.xpath("//p[contains(.,'Cons:')]/following-sibling::ul//text()").strings()
    if not cons:
        cons = data.xpath("//*[contains(., 'Cons')]/following-sibling::ul//li//text()").strings()
    if not cons:
        cons = data.xpath("//*[text()='Cons']/parent::div/following-sibling::ul/li").strings()
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "The Bad")]]/following-sibling::p[following-sibling::p[.//strong[contains(., "Wrap Up")]]]//text()').strings()
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "The Bad")]]//text()[not(contains(., "The Bad"))]').strings()
    for con in cons:
        review.add_property(type='cons', value=con)

    conclusion = data.xpath("//*[contains(.,'Conclusion:')]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//*[contains(.,'Conclusion')]/following-sibling::*/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//*[contains(.,'Final Thoughts')]/following-sibling::*//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Wrap Up")]]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "should you buy", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "It’s all you’ll likely need")]/following-sibling::p[not(.//a)]//text()').string(multiple=True)
    if conclusion:
        conclusion = re.sub(CLEANR, '', conclusion)
        conclusion = conclusion.replace('Conclusion:', '')
        if conclusion:  # after replacing "Conclusion:" by "" there might be empty string
            review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//p[@class="lead"]//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = ''
    lines = data.xpath("//div[@class='entry-content']/p[not(.//img)] | //div[@class='entry-content']/span[not(.//img)]")
    for line in lines:
        text = line.xpath('.//text()[not(preceding::p[.//strong[contains(., "Wrap Up")]])][not(preceding::text()[regexp:test(., "^conclusion", "i")])][not(preceding::text()[regexp:test(., "^final Thoughts", "i")])][not(preceding::text()[contains(., "The Bad")])][not(preceding::text()[contains(., "The Good")])][not(contains(., "The Good"))][not(preceding::h2[contains(., "verdict") or contains(., "It’s all you’ll likely need")])][not(preceding::h2[regexp:test(., "should you buy", "i")])]').string()
        if text:
            excerpt += text

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = re.sub(CLEANR, '', excerpt)
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    prods = data.xpath("//h1[@id='title']")
    if not prods:
        prods = data.xpath('//p[@id="title"] | //p[.//strong][not(contains(., "Sign up") or contains(., "Deals & More") or contains(., "Main") or contains(., "Android News"))]')
    if not prods:
        prods = data.xpath('//*[self::h1 or self::h2][@id="title"]')

    for prod in prods:
        name = prod.xpath(".//text()").string()
        if not name or "Top" in name:  # if don't page title
            continue

        product = Product()
        product.name = name
        product.url = context["url"]
        product.ssid = product.name.lower().replace(' ', '_').replace('-', '').replace('—', '').replace('__', '_')

        cats_list = data.xpath("//a[@class='taxonomy category']//text()")
        cats = ''
        for cat in cats_list:
            cats += cat.string().replace("News", "").replace('Reviews', '').strip() + "|"
        cats = cats.strip('| ')
        if not cats:
            cats = 'Tech'
        product.category = cats

        review = Review()
        review.url = product.url
        review.ssid = product.ssid
        review.title = product.name
        review.type = 'pro'

        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        excerpt = ''
        lines = prod.xpath('following-sibling::p[not(.//img)]')
        for line in lines:
            tag_a = line.xpath('.//a[regexp:test(., "buy the", "i")]').first()
            text = line.xpath('.//text()[not(regexp:test(., "buy the", "i"))]').string()
            if tag_a:
                product.url = tag_a.xpath('@href').string()
                break
            elif text:
                excerpt += text.strip()
                continue
            else:
                break    # I've seen mini-revs only with the one paragraph

        if excerpt:
            excerpt = re.sub(CLEANR, '', excerpt)
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
