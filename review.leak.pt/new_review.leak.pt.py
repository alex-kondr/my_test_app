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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.leak.pt/reviews/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[not(contains(., "Em destaque"))]//a[h2 or span/h3]')
    for rev in revs:
        title = rev.xpath('.//*[self::h2 or self::h3]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Análise – ', '').replace('Review – ', '').replace('Review: ', '').replace('Análise: ', '').split(': ')[0].split(' Review')[0].split(' – ')[0].replace(' review', '').replace('Mini-Review ', '').replace('Análise ', '').replace(' Análise', '').replace('Review ', '').replace('Quick-review ', '').replace('Mini-review ', '').replace('Análise ', '').replace('Análise/', '').replace(' (Review)', '').replace('(Análise) ', '').replace('(Review) ', '').replace('(Mini-Review) ', '').replace('(Mini-Análise) ', '').replace('Testámos a ', '').replace('Testámos o ', '').replace('[Review] ', '').replace('[Review/Análise]', '').replace('(Opinião) ', '').replace('(Em análise) ', '').replace('(Quick-Review) ', '').replace('(Re-Review) ', '').replace('(Preview) ', '').replace('(Especial) ', '').replace('(Mini-Teste) ', '').replace('Testei o ', '').replace(' (análise)', '').replace(' (Análise)', '').replace('(Analise)', '').replace('Analise ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '').replace('-analise', '')

    product.category = data.xpath('//span[@class="breadcrumb_last_link"]/a[not(regexp:test(., "Tech|Review"))]/text()').string()
    if not product.category:
        product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath('//span[contains(text(), "Por")]/a/@href[contains(., "/author/")]').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Nota final")]//text()[contains(., "/")]').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].split('/')[0].strip())
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('(//h4[contains(., "O que este teclado tem de bom?")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//h5[contains(., "Mais concretamente, temos")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//h3[contains(., "PROS")]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–<>')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "negativos")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//h5[contains(., "menos positivos")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//h3[contains(., "CONS")]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–<>')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('((//h4|//h3)[regexp:test(., "Conclusão|Condução|veredito|Veredicto", "i")])[last()]/following-sibling::p[not(contains(., "Nota final")) and text()]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('((//h4|//h3)[regexp:test(., "Vale a pena", "i")])[last()]/following-sibling::p[not(contains(., "Nota final")) and text()]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h4|//h3)[regexp:test(., "Conclusão|Condução|veredito|Veredicto", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('((//h4|//h3)[regexp:test(., "Vale a pena", "i")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-inner")]/p[not(contains(., "Nota final")) and text()]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
