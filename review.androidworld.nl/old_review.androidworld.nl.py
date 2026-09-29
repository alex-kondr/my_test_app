from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://androidworld.nl/reviews/", force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//a[@data-name="post"]')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8', max_age=0), process_review, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    prod_data = data.xpath('''//script[@class="yoast-schema-graph"]/text()''').string()
    if not prod_data:
        return

    prod_data = simplejson.loads(prod_data)
    product = Product()

    prods = prod_data.get("@graph")

    for prod in reversed(prods):
        if prod.get("@type") == "Review":
            product.name = prod.get("itemReviewed").get("name")
            manufacturer = prod.get("itemReviewed",{}).get("brand",{}).get("name")
            if manufacturer:
                product.manufacturer = manufacturer
            break
        elif prod.get("@type") == "Article":
            product.name = prod.get("headline").replace('Mini-review:', '').replace('Mini-review ', '').split('-review:')[0].split('review:')[0].split(': mid-ranger doet veel')[0].split(': meer klasse')[0].split(': tweede toptoestel')[0].split(': flinke accu')[0].split(': smartphone met')[0].split(': smartwatch voor')[0].split(': minder sprekend')[0].split(': terugkeer van')[0].split(': 24 uur met')[0].split(': herkenbare smartphone')[0].split(': wie niet')[0].split(': sterke comeback')[0].split(': verfijning van')[0].split(': en de laatste')[0].split(': met stip op')[0].split(': stijlvolle metalen')[0].split(': topsmartphones')[0].split(': de nieuwe ')[0].split(': verrassende ')[0].split(': (g)een grote')[0].split(': nieuwe LG')[0].split(': budget en')[0].split(': chique uitstraling')[0].split(': waar voor')[0].replace('reviews op Androidworld', '').replace(' videoreview', '').replace('Review:', '').replace('Preview nieuwe ', '').replace('Preview ', '').replace('Cameratest:', '').replace('(videoreview)', '').replace(' getest', '').replace('[video]', '').replace('Review ', '').replace(' review', '').split('PureView eerste')[0].split('preview van de')[0].split(": 'laatste kans'")[0].replace('Videoreview ', '')
    product.url = context['url']
    product.ssid = context['url'].split('/')[4]
    product.category = 'Technik'
    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid

    for prod in prods:
        if prod.get("@type") == "Article":
            review.title = prod.get("headline")

        if prod.get("@type") == "Article":
            review.date = prod.get("datePublished").split("T")[0]

        if prod.get("@type") == "Person":
            author = prod.get("name")
            author_url = prod.get("url")
            review.authors.append(Person(name=author, profile_url=author_url, ssid=author_url,))

        if prod.get("@type") == "Review":
            grade_overall = prod.get("itemReviewed").get("review").get("reviewRating").get("ratingValue")
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

        if prod.get("@type") == "Review":
            pros = prod.get("positiveNotes")
            if pros:
                pros = pros.get("itemListElement")
                for pro in pros:
                    pro = pro.get('name')
                    if pro != '':
                        review.add_property(type='pros', value=pro)

            cons = prod.get("negativeNotes")
            if cons:
                cons = cons.get("itemListElement")
                for con in cons:
                    con = con.get('name')
                    if con != '':
                        review.add_property(type='cons', value=con)

    pros = data.xpath('//h2[contains(., "Positieve punten")]/following-sibling::p[contains(.,"+ ") and following-sibling::h2[@class="wp-block-heading"]]//text()').string(multiple=True)
    if pros:
        pros = pros.split("+")
        for pro in pros:
            if pro != '':
                review.add_property(type='pros', value=pro)

    pros = data.xpath('//p[contains(.,"Pluspunten")]/following-sibling::p[following-sibling::p[contains(.,"Minpunten")]]//text()').string(multiple=True)
    if pros:
        pros = pros.split("→")
        for pro in pros:
            if pro != '':
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[contains(., "Negatieve punten")]/following-sibling::p[contains(.,"– ") and following-sibling::h2[@class="wp-block-heading"]]//text()').string(multiple=True)
    if cons:
        cons = cons.split("–")
        for con in cons:
            if con != '':
                review.add_property(type='cons', value=con)

    cons = data.xpath('//p[contains(.,"Minpunten")]/following-sibling::p[following-sibling::h2[@class="wp-block-heading"]]//text()').string(multiple=True)
    if cons:
        cons = cons.split("→")
        print(cons)
        for con in cons:
            if con != '':
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="wrap-inner flex flex-row max-w-[1062px]"]//p[not(@class)][1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Conclusie")]|//h3[contains(., "Conclusie")])/following-sibling::p[not(@id or starts-with(normalize-space(.), "+ ") or starts-with(normalize-space(.), "- ") or starts-with(normalize-space(.), "– ") or starts-with(normalize-space(.), "→ ") or starts-with(normalize-space(.), "Pluspunten") or starts-with(normalize-space(.), "Minpunten") or preceding-sibling::h2[contains(., "Alternatieven") or contains(., "kopen") or contains(., "Beschikbaarheid")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="wrap-inner flex flex-row max-w-[1062px]"]//p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)
        product.reviews.append(review)
        session.emit(product)