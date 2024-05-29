from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.itpro.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    pass