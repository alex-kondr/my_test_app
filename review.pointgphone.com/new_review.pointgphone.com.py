from agent import *
from models.products import *
import re


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
    session.queue(Request("http://www.pointgphone.com/tests-android/", use="curl",  force_charset="utf-8"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="post-link"]')
    for rev in revs:
        title = rev.xpath("h2/text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use="curl", force_charset="utf-8"), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset="utf-8"), process_revlist, dict())


def process_review(data, context, session):
    reviews = data.xpath("(//h4|//h3)[contains(.,'Points forts')]")
    if len(reviews) > 1:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2].split("-")[-1]
    product.category = data.xpath("//div[@class='penci-entry-categories']/span[@class='penci-cat-links']//text()").string() or "Tests et Dossiers"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//a[@class="author-name"]/text()').string()
    author_url = data.xpath('//a[@class="author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split("/")[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3|//h4)[regexp:test(., "Avantages|Points forts")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[contains(.,"Points positifs")]/following::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3|//h4)[regexp:test(., "Inconvénients|Points faibles")]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[contains(.,"Points négatifs")]/following::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//p|//h2)[regexp:test(., "Conclusion|verdict", "i")]/following-sibling::p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p|//h2)[regexp:test(., "Conclusion|verdict", "i")]//preceding-sibling::p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use="curl", force_charset="utf-8"), process_review_next, dict(product=product, review=review, excerpt=excerpt, url=next_url))

    elif excerpt:
        excerpt = remove_emoji(excerpt)
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    page = context["url"].split("/")[-2]
    title = review.title + ' - Page ' + page
    review.add_property(type="pages", value=dict(title=title, url=context["url"]))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.do(Request(next_page, use="curl", force_charset="utf-8"), process_review_next, dict(context, review=review, url=next_page))
        return

    pros = data.xpath('(//h3|//h4)[regexp:test(., "Avantages|Points forts")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[contains(.,"Points positifs")]/following::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3|//h4)[regexp:test(., "Inconvénients|Points faibles")]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[contains(.,"Points négatifs")]/following::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//p|//h2)[regexp:test(., "Conclusion|verdict", "i")]/following-sibling::p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p|//h2)[regexp:test(., "Conclusion|verdict", "i")]//preceding-sibling::p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@style or regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] = context['excerpt'] + ' ' + excerpt

    if context['excerpt']:
        if conclusion:
            context['excerpt'] = context['excerpt'].replace(conclusion, '')

        excerpt = remove_emoji(context['excerpt']).strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//h3[not(@class) and following::h4[(.//span[contains(.,"Points forts")])]]')
    for i, rev in enumerate(revs):
        product = Product()
        product.name = rev.xpath('text()').string()
        product.url = context['url']
        product.ssid = product.name.lower().replace(' ', '-')
        product.category = data.xpath("//div[@class='penci-entry-categories']/span[@class='penci-cat-links']//text()").string() or "Tests et Dossiers"

        review = Review()
        review.type = 'pro'
        review.url = product.url
        review.ssid = product.ssid
        review.title = context['title']

        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split("T")[0]

        author = data.xpath('//a[@class="author-name"]/text()').string()
        author_url = data.xpath("//a[@rel='author-name']/@href").string()
        if author and author_url:
            author_ssid = author_url.split("/")[-2]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('following-sibling::h3[regexp:test(., "Avantages|Points forts")][count(preceding-sibling::hr)={}]/following-sibling::ul[1]/li'.format(i))
        if not pros:
            pros = rev.xpath('following-sibling::h4[regexp:test(., "Avantages|Points forts")][count(preceding-sibling::hr)={}]/following-sibling::ul[1]/li'.format(i))

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('following-sibling::h3[regexp:test(., "Inconvénients|Points faibles")][count(preceding-sibling::hr)={}]/following-sibling::ul[1]/li'.format(i))
        if not cons:
            cons = rev.xpath('following-sibling::h4[regexp:test(., "Inconvénients|Points faibles")][count(preceding-sibling::hr)={}]/following-sibling::ul[1]/li'.format(i))

        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::hr)={}][not(regexp:test(., "http://|\[penci|\[review/\[amazon"))]//text()'.format(i)).string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(excerpt)
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
