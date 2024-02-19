from agent import *
from models.products import *
import re


XCAT = ['NEWS']


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.qobuz.com/fr-fr/magazine'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//nav[@id="navbar"]//a[normalize-space()]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="section-cards-element"]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('.//a[@class=""]/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@class="store-paginator__button next "]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.name = data.xpath('//h1[@class="magazine-header-title"]/text()').string().replace('Test (avec vidéo-Qobuz !) de', '').replace('Test complet avec vidéo Qobuz du', '').replace('Test avec Qobuz-vidéo du', '').replace('(test avec vidéo / 299 €)', '').replace('M\éga-test avec vidéo du', '').replace('Méga test avec', '').replace('Méga test de', '').replace('Méga test du', '').replace('Test duo', '').replace('Test Qobuz des', '').replace('Test audio du', '').replace('Test audio de', '').replace('Test audio', '').replace('Test du casque', '').replace('Test casque', '').replace('Test avec', '').replace('Test de', '').replace('Test du', '').replace('Testez votre', '').replace('Testez', '').replace('Mini tests', '').replace('Test', '').strip()
    if not product.name or len(product.name) < 3:
        product.name = context['title'].replace('Test (avec vidéo-Qobuz !) de', '').replace('Test complet avec vidéo Qobuz du', '').replace('Test avec Qobuz-vidéo du', '').replace('(test avec vidéo / 299 €)', '').replace('M\éga-test avec vidéo du', '').replace('Méga test avec', '').replace('Méga test de', '').replace('Méga test du', '').replace('Test duo', '').replace('Test Qobuz des', '').replace('Test audio du', '').replace('Test audio de', '').replace('Test audio', '').replace('Test du casque', '').replace('Test casque', '').replace('Test avec', '').replace('Test de', '').replace('Test du', '').replace('Testez votre', '').replace('Testez', '').replace('Mini tests', '').replace('Test', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url
    review.date = data.xpath('//time/@datetime').string()

    author = data.xpath('//div[@class="magazine-header-author"]/a/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div/@rating-star').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5))

    pros = data.xpath('//div[@class="pros-container"]/span')
    if not pros:
        pros = data.xpath('//span[@class="hl_green" and not(contains(., "Les +") or contains(., "LES +"))]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons-container")]/span')
    if not cons:
        cons = data.xpath('//span[@class="hl_red" and not(contains(., "Les -") or contains(., "LES -"))]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//section[@class="story-row story-desc"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary)
        review.add_property(type='summary', value=summary)

    conclusions = data.xpath('(//p[@class="features-value"]|//div[@class="story-row story-body" and not(contains(., "Facebook"))]//p[contains(., "Conclusion")]/following-sibling::p[.//b]|//div[@class="story-row story-body" and not(contains(., "Facebook"))]//p[contains(., "Conclusion :")]|//div[@class="story-row story-body" and not(contains(., "Facebook")) and .//h2[contains(., "Conclusion")]]/following::p[.//b])[normalize-space()]')
    if conclusions:
        conclusions = [conclusion.xpath('.//text()').string(multiple=True) for conclusion in conclusions]
        conclusion = remove_emoji(' '.join(conclusions).replace('Conclusion', '').strip())
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="story-row story-body" and not(contains(., "Facebook") or .//span[contains(@class, "hl")] or contains(., "Prix :") or contains(., "Amplification :") or contains(., "Connectivité :") or contains(., "Streaming :"))]//p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        for conclusion in conclusions:
            excerpt = excerpt.replace(conclusion, '').replace('Conclusion', '')

        excerpt = remove_emoji(excerpt)
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
