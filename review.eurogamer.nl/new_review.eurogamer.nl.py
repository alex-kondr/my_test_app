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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.eurogamer.net/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "link link--expand")]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Next page"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' review: ')[0].replace(' review', '').replace(' Review', '').split(' - ')[0].split(' Preview: ')[0].replace('Review: ', '').replace(' re-review', '').replace('Hardware Test:', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.manufacturer = data.xpath('//li[strong[contains(., "Developer:")]]/text()').string()

    product.category = data.xpath('//li[strong[contains(., "Availability:")]]/a/text()').strings()
    if product.category:
        product.category = '|'.join(product.category).replace('|Official Launcher', '')
    if not product.category or '...' in product.category:
        product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
    grade_best = data.xpath('//div[@class="review_rating"]//*[contains(@class, "max_value")]/text()').string()
    if grade_overall:
        grade_best = float(grade_best) if grade_best else 5.0
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=grade_best))

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[strong[contains(., "Conclusions")]]|//h2[contains(., "Conclusions")])/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "body_content")]/div[not(@class)]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p[strong[contains(., "Conclusions")]]|//h2[contains(., "Conclusions")])/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body_content")]//p//text()').string(multiple=True)

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        title = review.title + " - Pagina 1"
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(grade_overall=grade_overall, excerpt=excerpt, review=review, product=product, page=2))

    else:
        if excerpt and conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        context['excerpt'] = excerpt
        context['review'] = review
        context['product'] = product

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        if not context.get('grade_overall'):
            grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
            grade_best = data.xpath('//div[@class="review_rating"]//*[contains(@class, "max_value")]/text()').string()
            if grade_overall:
                grade_best = float(grade_best) if grade_best else 5.0
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=grade_best))

        if data.xpath('//a[contains(@href, "?page=") and regexp:test(., "Conclusions|Verdict")]/@href').string() == data.response_url:
            conclusion = data.xpath('//div[contains(@class, "body_content")]//p//text()').string(multiple=True)
            if conclusion:
                conclusion = remove_emoji(conclusion).strip()
                review.add_property(type='conclusion', value=conclusion)
        else:
            conclusion = data.xpath('(//p[strong[contains(., "Conclusions")]]|//h2[contains(., "Conclusions")])/following-sibling::p//text()').string(multiple=True)
            if not conclusion:
                conclusion = data.xpath('//div[contains(@class, "body_content")]/div[not(@class)]//text()').string(multiple=True)

            if conclusion:
                conclusion = remove_emoji(conclusion).strip()
                review.add_property(type='conclusion', value=conclusion)

            excerpt = data.xpath('(//p[strong[contains(., "Conclusions")]]|//h2[contains(., "Conclusions")])/preceding-sibling::p//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath('//div[contains(@class, "body_content")]//p//text()').string(multiple=True)

            if excerpt:
                context['excerpt'] += " " + excerpt

                if conclusion:
                    context['excerpt'] = context['excerpt'].replace(conclusion, '').strip()

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, page=page + 1))

    elif context['excerpt']:
        context['excerpt'] = remove_emoji(context['excerpt']).strip()
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
