from agent import *
from models.products import *


def run(contex, session):
    session.queue(Request('http://www.newgadgets.de/category/testbericht/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="row"]//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "Ältere Beiträge")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('(Gewinnspiel inside!)', '').replace('vorgestellt und bei uns im test', '').replace('im Kamera-Test in Florenz', '').replace('Unser Testrechner auf', '').replace(': Testergebnis schnell und leise', '').replace('Der Umstiegstest von', '').replace(': Falltest & Wassertest', '').replace('im Praxistest', '').replace('im Review', '').replace('CES 2013:', '').replace('Ausführlicher', '').replace('Vergleichstest:', '').replace('Unboxing', '').replace('Größenvergleich', '').replace('Getestet:', '').replace('Härtetest', '').replace('Test:', '').replace('Testbericht:', '').replace('Angetestet:', '').replace('Computex 2013:', '').replace('Hands On', '').replace('Videotestbericht', '').replace('Game Review', '').replace('Im Test:', '').replace('im Test', '').replace('im test', '').replace('Video:', '').replace('(mit Video)', '').replace('getestet', '').replace('Kurztest', '').replace('Lesertest:', '').replace('Testbericht', '').replace('Video', '').replace('mit dem', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Technik'

    product.url = data.xpath('//a[contains(., "Klick") or contains(., "Amazon") or contains(., "Mediamarkt")]/@href').string()
    if not product.url:
        product.url = context['url']

    cats = data.xpath('//span[@class="category"]/a/text()[not(contains(., "Testbericht") or contains(., "Zubehör"))]').strings()
    if cats:
        product.category = '|'.join(cats)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author-name"]/a/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[contains(., "Positiv")]/text()[contains(., "+")]')
    if not pros:
        pros = data.xpath('//p[contains(., "Positiv")]/following-sibling::p[1]/text()')
    for pro in pros:
        pro = pro.string().strip(' +•')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Negativ")]/text()[contains(., "-")]')
    if not cons:
        cons = data.xpath('//p[contains(., "Negativ")]/following-sibling::p[1]/text()')
    for con in cons:
        con = con.string().replace('•', '').strip(' -')
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(.,"| Fazit") and not(@class)]/following-sibling::p[not(contains(., "Positiv") or contains(., "•") or contains(., "Negativ") or contains( ., "Klick") or contains(., "Amazon *") or contains(., ">>") or .//input)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h2[contains(.,"Fazit") and not(@class)]|//p[.//strong[contains(., "Fazit")]])/following-sibling::p[not(contains(., "Positiv") or contains(., "•") or contains(., "Negativ") or contains( ., "Klick") or contains(., "Amazon *") or contains(., ">>") or .//input)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(.,"| Fazit") and not(@class)]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h2[contains(.,"Fazit") and not(@class or contains(., "|"))]|//p[.//strong[contains(., "Fazit")]])/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]//p[not(contains(., "Positiv") or contains(., "•") or contains(., "Negativ") or contains( ., "Klick") or contains(., "Amazon") or .//input)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
