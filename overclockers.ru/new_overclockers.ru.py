from agent import *
from models.products import *
import re


XCAT = ["Все статьи", "FAQ", "Институт оверклокинга", "Руководства", "События", "Сайт", "Всё про..."]


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://overclockers.ru/lab', use='curl', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath("//div[contains(@class, 'content-menu')]//div[@class='ui horizontal list']/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    for rev in data.xpath("//div[@class='item article-wrap']/div[@class='content']"):
        title = rev.xpath("a//text()").string(multiple=True)
        url = rev.xpath("a/@href").string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    next = data.xpath("//div[@class='ui pagination menu']/a[@class='item next']/@href").string()
    if next:
        session.queue(Request(next, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = data.xpath('//a/@data-what-id').string()
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@href, '/author/')]/span/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating-value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[contains(@class, "sub-header")]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    last_page = ''
    pages = data.xpath('//div[@class="ui list"]//div[@class="content"]')
    for page in pages:
        title = page.xpath('.//text()').string()
        last_page = page.xpath('a/@href').string()
        if title and last_page:
            review.add_property(type='pages', value=dict(title=title, url=last_page))
        elif title:
            review.add_property(type='pages', value=dict(title=title, url=product.url))

    conclusion = data.xpath('(//h3|//h1)[contains(., "Заключение")]/following-sibling::p[not(regexp:test(., "По итогам обзора|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//h1)[contains(., "Заключение")]/preceding-sibling::p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[@itemprop="articleBody"]//p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:|По итогам обзора|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)

    if last_page:
        session.do(Request(last_page, use='curl', max_age=0), process_lastpage, dict(product=product, review=review, excerpt=excerpt))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_lastpage(data, context, session):
    strip_namespace(data)

    review = context['review']

    conclusion = data.xpath('(//h3|//h1)[contains(., "Заключение")]/following-sibling::p[not(regexp:test(., "По итогам обзора|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//h1)[contains(., "Заключение")]/preceding-sibling::p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[@itemprop="articleBody"]//p[not(regexp:test(., "CPU-Z:|AIDA64|Cinebench|PCMark 10:|3DMark|Winrar|7-Zip|Geekbench|CrystalDisk|Benchmark:|По итогам обзора|P.S.|Дискуссии по теме|JavaScript") or .//script)]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] = context.get('excerpt', '') + ' ' + excerpt

    if context['excerpt']:
        excerpt = remove_emoji(context['excerpt']).strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
