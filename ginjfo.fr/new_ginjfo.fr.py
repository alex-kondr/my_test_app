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
    session.queue(Request('https://www.ginjfo.com/dossiers', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test ', '').strip()
    product.ssid = context['url'].split('-')[-1]
    product.category = data.xpath('//a[contains(@class, "post-cat") and not(contains(., "Trucs et astuces"))]/text()').string()

    product.url = data.xpath('//a[regexp:test(@href, "amzn.to/|tidd.ly/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="meta-author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="meta-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].replace('%', '')) / 20
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('h5//text()').string()
        grade_val = float(grade.xpath('.//span/@style').string().split(':')[-1].replace('%', '')) / 20
        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    awards = data.xpath('//figure[@class="gallery-item"]')
    if not awards:
        awards = data.xpath('//a[img[contains(@alt, "Top")]]')

    for award in awards:
        title = award.xpath('figcaption/text()').string() or award.xpath('img/@alt').string()
        img = award.xpath('.//a/@href').string() or award.xpath('@href').string()

        if title and 'Top' in title:
            review.add_property(type='awards', value=dict(title=title, img=img))

    summary = data.xpath('//h2[@class="entry-sub-title"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="review-short-summary"]/p//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    context['excerpt'] = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review, product=product, page=2))

    else:
        context['review'] = review

        context['product'] = product

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = data.xpath('//h2[not(@class)]/text()').string() or review.title + '- Pagina ' + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        prod_url = data.xpath('//a[regexp:test(@href, "amzn.to/|tidd.ly/")]/@href').string()
        if prod_url:
            context['product'].url = prod_url

        grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = data.xpath('//div[@class="review-item"]')
        for grade in grades:
            grade_name = grade.xpath('h5//text()').string()
            grade_val = float(grade.xpath('.//span/@style').string().split(':')[-1].replace('%', '')) / 20
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

        awards = data.xpath('//figure[@class="gallery-item"]')
        if not awards:
            awards = data.xpath('//a[img[contains(@alt, "Top")]]')

        for award in awards:
            title = award.xpath('figcaption/text()').string() or award.xpath('img/@alt').string()
            img = award.xpath('.//a/@href').string() or award.xpath('@href').string()

            if title and 'Top' in title:
                review.add_property(type='awards', value=dict(title=title, img=img))

        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="review-short-summary"]/p//text()').string(multiple=True)

        if conclusion:
            conclusion = remove_emoji(conclusion).strip()
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)

        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review, page=page+1))

    elif context['excerpt']:
        context['excerpt'] = remove_emoji(context['excerpt']).strip()
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
