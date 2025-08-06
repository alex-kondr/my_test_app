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
    session.queue(Request('https://www.runnersworld.de/ausruestung/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "teaserHeader_teaser")]/div/a')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[.//h3]')
    for rev in revs:
        title = rev.xpath('.//h3//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + 'seite/{}/'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' im Test', '').replace('Im Test: ', '').replace(' im Praxistest', '').replace(' im ersten Test', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-im-test', '')
    product.category = context['cat']

    product.url = data.xpath('//p[contains(., "Hier bestellen:")]//a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="article:published_time"]/@content|//div[contains(., "Veröffentlicht am ")]/text()').string()
    if date:
        review.date = date.split('T')[0].split(' am ')[-1]

    authors = data.xpath('(//a|//span)[contains(@class, "article-author")]')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()

        if author_name and author_url:
            author_name = author_name.strip(' ,.')
            author_ssid = author_url.split('/')[-2]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

        elif author_name:
            author_name = author_name.strip(' ,.')
            review.authors.append(Person(name=author_name, ssid=author_name))

    pros = data.xpath('//h3[contains(., "Vor- und Nachteile")]/following::p[contains(., "✅")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–✅')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–❌')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h2]//div[contains(@class, "text_text")]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[p[contains(., "Fazit")]]/following-sibling::div/p[not(regexp:test(., "Hier bestellen:|✅|❌|Preis:|Fazit|Sprengung:|Gewicht:"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "article-text")]/div/p[not(regexp:test(., "Hier bestellen:|✅|❌|Preis:|Fazit") or (preceding::h3|preceding::p)[regexp:test(., "Fazit|Die wichtigsten Daten")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
