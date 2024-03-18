from agent import *
from models.products import *


XCAT = ['Behandlungen ', 'Beratung ', 'Hautberatungsteam', 'Werte', 'Magazin']


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.drhauschka.de/'), process_frontpage, dict())



def process_frontpage(data, context, session):
    cats = data.xpath('')
    for cat in cats:
        name = cat.xpath('').string(multiple=True).replace('Zur Kategorie', '').strip()

        if name not in XCAT:
            sub_cats = cat.xpath('')
            for sub in sub_cats:
                su
