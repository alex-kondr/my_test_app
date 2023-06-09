from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())
    
    
def process_frontpage(data, context, session):
    cats1 = data.xpath("//ul[@class='site-header__nav__285 site-header__nav__menu no-bullet']/li[contains(@class, 'drop-down')]")
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        print('name1=', name1)
        cats2 = cat1.xpath(".//a[contains(@class, 'top_level_link')]")
        print('len_cats2=', len(cats2))
        
        # for cat2 in cats2:
        #     name2 = cat2.xpath("a//text()").string()
        #     cats3 = cat2.xpath("ul/li/a")
        #     for cat3 in cats3:
        #         name3 = cat3.xpath(".//text()").string()
        #         url = cat3.xpath("@href").string()
        #         session.queue(Request(url), process_category, dict(cat=name1+"|"+name2+"|"+name3))