# -*- coding: utf8 -*-
from agent import *
from models.products import *
            
def process_category(data, context, session):
    for link in data.xpath('//ul[@class="front-posts-list"]//h2//a'):
        url=link.xpath('@href').string()
        name=link.xpath('text()').string()
        if url and name:
            bad_list = [' im Test – ',' – ']
            for item in bad_list:
                if item in name:
                    namex = name.split(item)[0]
                    if len(namex) == 0:
                        name = name.split(item)[1]
                    else:
                        name = namex
                    break

            bad_list2 = ['Testbericht:',' im Test','Testbericht','ausführlichen ','im ', 'Video: ',
            '(mit Video)', 'Videotestbericht', 'zum',' Game Review','Im Test:','Das ','Angetestet: ',
            'Computex 2013:','Hands On','Video',' mit dem',' (Gewinnspiel inside!)','Vergleichstest:',
            'mit ','Unboxing' ' und ','Größenvergleich','Härtetest','getestet','CES 2013: ','Ausführlicher',
            ' zur ']
            for item in bad_list2:
                if item in name:
                    name = name.replace(item, '')

            if 'test' in url or 'hands' in url or 'review' in url:
                session.queue(Request(url),process_product,dict(context,url=url,name=name))

    # Next page
    next=data.xpath('//div[@class="pagination"]//a[contains(text(),"›")]//@href').string()
    if next:
        session.do(Request(next), process_category, {})
            
def process_product(data, context, session):
    product=Product()
    product.name=context['name']
    product.url=context['url']
    product.ssid=product.name + ' ' + product.url
    product.category='unknown'
    product.manufacturer=''
    
    review=Review()
    review.product=product.name
    review.url=product.url

    # Publish date
    pub_date=data.xpath('//div[@class="tooltip"]//small/text()').string()
    if pub_date:
        review.date=pub_date[2:-4].replace('.', '')
    else:
        review.date='unknown'

    # Author
    author=data.xpath('//div[@class="tooltip"]//small//a//text()').string(multiple=True)
    author_ssid=data.xpath('//div[@class="tooltip"]//small//a//@href').string(multiple=True)
    if author and author_ssid:
        review.authors.append(Person(name=author, ssid=author_ssid))
    else:
        review.authors.append(Person(name='unknown', ssid='unknown'))
        
    # Type
    review.type='pro'
         
    # Ssid
    review.ssid=product.ssid

    # Summary
    summary=data.xpath('//div[@class="single-content"]//p//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary',value=summary))

    # Conclusion
    conc_list = [
    '//div[@class="single-content"]//h2[contains(text(), "Fazit")]//following-sibling::p//text()',
    '//div[@class="single-content"]//h2//strong[contains(text(), "Fazit")]//..//following-sibling::p//text()',
    '//div[@class="single-content"]//p//strong[contains(text(), "Fazit")]//..//following-sibling::p//text()']

    for item in conc_list:
        conclusion = data.xpath(item).string(multiple=True)
        if conclusion:
            review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
            break

    product.reviews.append(review)
    
    if product.reviews and summary:
        session.emit(product)
    
def run(context, session):
    session.queue(Request('http://www.newgadgets.de/category/testbericht/'), process_category, {})
