from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.eurogamer.it/archive/reviews'), process_frontpage, {})


def process_frontpage(data, context, session):
    for prod in data.xpath("//a[@class='link_overlay']"):
        context['name'] = prod.xpath("@title").string()
        context['url'] = prod.xpath("@href").string()
        if context['name']:
            session.queue(Request(context['url']), process_review, context)

    next_page_links = data.xpath("//div[@class='next']//a")
    if not next_page_links:
        return

    next_page = next_page_links.first().xpath("@href").string()
    if next_page:
        session.queue(Request(next_page), process_frontpage, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]

    list_items = data.xpath("//div[contains(@class, 'article_body_content')]/ul/li")
    category = None

    for item in list_items:
        cat_text = item.xpath("text()").string()

        if not cat_text:
            continue

        if "Versione provata" in cat_text or "Versione Provata" in cat_text:
            category = cat_text
            break

    if category:
        product.category = "Games|" + category.replace('Versione provata: ', '').replace('Versione Provata: ', '')
    else:
        product.category = "Games"

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.url = context['url']
    review.type = 'pro'

    review_date = data.xpath("//div[@class='published_at' or @class='updated_at']//time/@datetime")
    if review_date:
        review.date = review_date.string().split(' ')[0]

    author_name = data.xpath("//div[@class='author']//span[@class='name']/a//text()").string()
    author_url = data.xpath("//div[@class='author']//span[@class='name']/a/@href").string()
    if author_name:
        review.authors.append(Person(name=author_name, url=author_url, ssid=author_url.split('/')[-1]))

    summary = data.xpath("//div[@class='details']//span[@class='strapline']//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary))

    excerpt_paragraphs = data.xpath("//div[@class='article_body_content']//p[not(@class='score')]")
    excerpt = ""
    
    for item in excerpt_paragraphs:
        text = item.xpath(".//text()").string(multiple=True)
        
        if not text:
            continue
        
        if "RAM" in text:
            continue
        if "Storage" in text:
            continue
        if "Rete" in text:
            continue
        if "Caratteristiche Overclock" in text:
            continue
        if "Audio" in text:
            continue
        if "Risposta frequenza" in text:
            continue
        if "Connettori" in text:
            continue
        if "Impedenza nominale" in text:
            continue
        if "Driver" in text:
            continue
        if "Peso" in text:
            continue
        if "Processori" in text:
            continue
        if "Supporto Multi-GPU" in text:
            continue
        if "Slot di Espansione" in text:
            continue
        if "Regia" in text:
            continue
        if "Cast" in text:
            continue
        if "Distribuzione" in text:
            continue
        if "Genere" in text:
            continue
        if "Sviluppatore" in text:
            continue
        if "Publisher" in text:
            continue
        if "Disponibilità" in text:
            continue
        if "Versione provata" in text:
            continue
        
        excerpt += text
    
    page_count = data.xpath("//div[@class='page_counter']//span[@class='max']")
    
    if page_count:
        page_count = int(page_count.first().xpath(".//text()").string())
        for page in range(2, page_count + 1):
            review.properties.append(ReviewProperty(type="pages", value=dict(url=product.url + "?page=" + str(page))))

        session.do(Request(product.url + "?page=" + str(page_count)), process_review_next, {"excerpt": excerpt, "review": review})

    elif excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

    grade = data.xpath("//span[@class='review_rating_value']//text()").string()
    if grade:
        best = data.xpath("//span[@class='review_rating_max_value']//text()").string()
        if best:
            review.grades.append(Grade(name="Score", value=float(grade), worst=float(0), best=float(best), type='overall'))

    if excerpt:
        product.reviews.append(review)
        session.emit(product)


def process_review_next(data, context, session):
    excerpt = context["excerpt"]
    review = context["review"]
            
    excerpt_new = data.xpath("//div[@class='article_body_content']//p[not(@class='score')]//text()").string(multiple=True)
    if excerpt_new:
        excerpt += excerpt_new
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    
    grade = data.xpath("//span[@class='review_rating_value']//text()").string()
    if grade:
        best = data.xpath("//span[@class='review_rating_max_value']//text()").string()
        if best:
            review.grades.append(Grade(name="Score", value=float(grade), worst=float(0), best=float(best), type='overall'))
