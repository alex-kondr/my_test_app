from agent import *
from models.products import *
debug = True


def process_productlist(data, context, session):
    for prod in data.xpath("//div[@class='post-inner post-hover']/h2[@class='post-title']/a"):
        url = prod.xpath("@href").string()
        name = prod.xpath(".//text()").string(multiple=True)
        session.queue(Request(url, use='curl'), process_product, dict(url=url, name=name))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-2].replace('.html', '')
    product.category = data.xpath("//li[@class='category']/a[last()]//text()").string()
    product.url = context['url']
    
    review = Review()
    review.title = context['name']
    review.date = data.xpath("//div[@class='post-inner group']/p[@class='post-byline']//text()").string(multiple=True).split('· ')[1]
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    
    authors = data.xpath("//div[@class='post-inner group']/p[@class='post-byline']/a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    excerpt = data.xpath("//div[@class='entry-inner']//p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='entry-inner']//div//text()").string(multiple=True)
    if excerpt:
        excerpt = excerpt.split('Condividi')[0]
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    grades_list = ['Giocabilità', 'Grafica', 'Sonoro', 'Longevità', 'Globale']
    for grade_text in grades_list:
        grade = data.xpath("//div[@class='entry-inner']//p[contains(., '" + grade_text + ": ')]//text()").string(multiple=True)
        if not grade:
            grade = data.xpath("//div[@class='entry-inner']/div/span[contains(., '" + grade_text + ": ')]//text()").string(multiple=True)
        if grade:
            grade = grade.split(grade_text + ': ')[1].split('/')[0].split(' ')[0].split('\n')[0]
            if grade:
                try:
                    grade = float(grade)
                except:
                    continue
                if grade_text == 'Globale':
                    review.grades.append(Grade(type='overall', name=grade_text, value=grade, best=10.0))
                else:
                    review.grades.append(Grade(name=grade_text, value=grade, best=10.0))
    
    pros = data.xpath("//div[@class='entry-inner']//p//strong[contains(., 'Pro e contro')]/../following-sibling::p[1]//text()")
    for pro in pros:
        pro = pro.string().replace('+', '').strip()
        review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//div[@class='entry-inner']//p//strong[contains(., 'Pro e contro')]/../following-sibling::p[2]//text()")
    for con in cons:
        con = con.string().replace('- ', '').strip()
        review.add_property(type='cons', value=con)
    
    product.reviews.append(review)
    session.emit(product)


def run(context, session):
    session.queue(Request('https://www.thetotalsite.it/c/recensioni/recensioni-videogiochi/', use='curl'), process_productlist, {})
