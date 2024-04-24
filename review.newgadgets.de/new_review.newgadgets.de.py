from agent import *
from models.products import *


def run(contex, session):
    session.queue(Request('http://www.newgadgets.de/category/testbericht/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="row"]//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, ur=url))

    next_url = data.xpath('//a[contains(text(), "Ältere Beiträge")]/@href').string()
    if next_url:
        session.queue(Request(url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('(Gewinnspiel inside!)', '').replace('CES 2013:', '').replace('Ausführlicher', '').replace('Vergleichstest:', '').replace('Unboxing', '').replace('Größenvergleich', '').replace('Härtetest', '').replace('Test:', '').replace('Testbericht:', '').replace('Angetestet:', '').replace('Computex 2013:', '').replace('Hands On', '').replace('Videotestbericht', '').replace('Game Review', '').replace('Im Test:', '').replace('im Test', '').replace('Video:', '').replace('(mit Video)', '').replace('getestet', '').replace('Testbericht', '').replace('Video', '').replace('mit dem', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Technik'

    product.url = data.xpath('//a[contains(., "Klick")]/@href').string()
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

    pros = data.xpath('//p[contains(., "Positiv")]/following-sibling::p[1]/text()')
    for pro in pros:
        pro = pro.string().replace('•', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Negativ")]/following-sibling::p[1]/text()')
    for con in cons:
        con = con.string().replace('•', '').strip()
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(.,"Fazit")]/following-sibling::p[not(contains(., "Positiv") or contains(., "•") or contains(., "Negativ") or contains( ., "Klick"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)