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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('http://www.funkykit.com/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url.replace('dev1.', ''), use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Review: ', '').replace('Review of the ', '').replace(' Preview', '').replace(' Review', '').replace('®Review', '').replace(' review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = data.xpath('//span[contains(@class, "cat-links")]/a[not(regexp:test(., "Reviews|Unboxing|Articles|Featured"))]/text()').string() or 'Tech'
    product.manufacturer = data.xpath('//div[strong[contains(., "Brand")]]/text()').string()

    product.url = data.xpath('//a[contains(@class, "review-btnbuy")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "entry-meta-item")]/span[contains(@class, "author")]//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "entry-meta-item")]/span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    context['excerpt'] = data.xpath('(//div[contains(@class, "entry-content")]/p[not(regexp:test(., "(^\s*Conclusion|^\s*Pros|^\s*Cons|^\s*Final word|^\s*Final tho)", "i"))][not(a[contains(@href, "amzn") or contains(@href, "amazon")])][not(contains(., "Related article") or contains(., "More information on"))] | //div[contains(@class, "entry-content")]/blockquote[preceding-sibling::h3[contains(., "Benchmark")]])[not(preceding-sibling::*[contains(., "Verdict") or contains(., "Conclusion") or contains(., "Final Words") or strong[contains(., "Final words")]])]//text()').string(multiple=True)

    pages = data.xpath('//nav[contains(@class, "pagination")]/div/*')
    if pages:
        for page in pages:
            page_num = page.xpath('.//text()').string(multiple=True)

            page_url = page.xpath('@href').string()
            if page_url:
                page_url = page_url.replace('dev1.', '')
            else:
                page_url = review.url

            title = review.title + " - Pagina " + page_num
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(page_url, use='curl', force_charset='utf-8'), process_review_last, dict(context, review=review, product=product, pages=True))

    else:
        context['review'] = review
        context['product'] = product
        process_review_last(data, context, session)


def process_review_last(data, context, session):
    strip_namespace(data)

    review = context['review']

    grade_overall = data.xpath('(//div[contains(@class, "review-score-num")])[1]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[strong[contains(., "SCORE")]]/following-sibling::p[1]//text()').string()

    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0].replace(',', '.').strip())
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type="overall", value=grade_overall, best=10.0))

    grades = data.xpath('(//ul[@class="penci-review-number"])[1]/li')
    for grade in grades:
        grade_name = grade.xpath('.//div[contains(@class, "-point")]/text()').string()
        grade_value = grade.xpath('.//div[contains(@class, "-score")]/text()').string()
        if grade_name and grade_value:
            grade_name = remove_emoji(grade_name).replace('&amp;','&').strip('(. )')
            grade_value = float(grade_value.replace(',', '.').strip('( )'))

            if grade_value <= 10:
                review.grades.append(Grade(name=grade_name, value=grade_value, best=10.0))
            else:
                review.grades.append(Grade(name=grade_name, value=grade_value, best=grade_value))

    pros = data.xpath('(//div[contains(@class, "review-good")]/ul)[1]/li')
    if not pros:
        pros = data.xpath('(//p[normalize-space(strong/text())="Pros:"]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.:;•,–')
            if pro and pro not in ['None', 'No', 'Zero', 'Couldn’t find any', "Can't find any"]:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[contains(@class, "review-bad")]/ul)[1]/li')
    if not cons:
        cons = data.xpath('(//p[normalize-space(strong/text())="Cons:"]/following-sibling::*)[1]/li ')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.:;•,–')
            if con and con not in ['None', 'No', 'Zero', 'Couldn’t find any', "Can't find any"]:
                review.add_property(type='cons', value=con)

    award = data.xpath('//div[contains(@class, "entry-content")]//img[regexp:test(@src,"(choice|recommend)", "i")]//@src').string()
    if award:
        review.add_property(type='awards', value=dict(image_src=award))

    summary = data.xpath('(//div[strong[contains(., "Description")]])[1]/text()[normalize-space()]').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        if len(summary) > 2:
            review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "(^\s*Conclusion|^\s*Pros|^\s*Cons|^\s*Final word|^\s*Final tho)", "i"))][preceding-sibling::*[contains(., "Verdict") or contains(., "Conclusion") or contains(., "Final Words") or strong[contains(., "Final words")]]][not(contains(., "SCORE"))][not(preceding-sibling::p[contains(., "SCORE")])][not(a[contains(@href, "amzn") or contains(@href, "amazon")])][not(contains(., "Related article") or contains(., "More information on") or contains(., "Thanks for reading!"))][not(strong[regexp:test(., "^\s*Similar") or regexp:test(., "^\s*Silimar")])][not(regexp:test(., "buy", "i") and regexp:test(., "at", "i")) or not(regexp:test(., "can buy", "i") and regexp:test(., "from Amazon", "i"))][not(contains(., "http"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        if len(conclusion) > 2:
            review.add_property(type='conclusion', value=conclusion)

    if context.get('pages'):
        excerpt = data.xpath('(//div[contains(@class, "entry-content")]/p[not(regexp:test(., "(^\s*Conclusion|^\s*Pros|^\s*Cons|^\s*Final word|^\s*Final tho)", "i"))][not(a[contains(@href, "amzn") or contains(@href, "amazon")])][not(contains(., "Related article") or contains(., "More information on") or contains(., "Verdict") or contains(., "Conclusion") or contains(., "Final Words") or strong[contains(., "Final words")])] | //div[contains(@class, "entry-content")]/blockquote[preceding-sibling::h3[contains(., "Benchmark")]])[not(preceding-sibling::*[contains(., "Verdict") or contains(., "Conclusion") or contains(., "Final Words") or strong[contains(., "Final words")]])]//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] = context.get('excerpt', '') + " " + excerpt

    if context['excerpt']:
        excerpt = remove_emoji(context['excerpt']).strip()
        if len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            product = context['product']
            product.reviews.append(review)

            session.emit(product)
