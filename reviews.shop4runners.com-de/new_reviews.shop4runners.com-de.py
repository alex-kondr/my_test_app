from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://shop4runners.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('')
    
    
    """
/ /div[contains(@class, "category-item")]
 div[@class="lg:p-3"]/text()
 .//div[@class="nav__column"]//a[@class="nav-item__title uppercase no-underline"]
 .//div[contains(@class, "nav-item--and-text")]
  .//div[@class="nav-item__title uppercase"]/text()
  .//div[@class="nav-item nav-item__link"]/a
   text()
   @href
    """