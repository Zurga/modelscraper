from modelscraper.components import Scraper, Model, Attr
from modelscraper.parsers import HTMLParser
from modelscraper.sources import WebSource
from modelscraper.databases import MongoDB

list_url = "https://www.erowid.org/experiences/exp.cgi?ShowViews=1&Cellar=0&Start=0&Max=1"
listing_source = WebSource(name='listing', urls=[list_url], domain='https://www.erowid.org/experiences/')
report_source = WebSource()
parser = HTMLParser()

report_listing = Model(
    source=listing_source,
    name='report_url', selector=parser.select('.exp-list-table tr'),
    emits=report_source,
    attrs=(
        Attr(name='url', func=parser.url(selector='td:nth-of-type(2) a')),
        Attr(name='title', func=parser.text(selector='td:nth-of-type(2) a')),
        Attr(name='rating', func=parser.attr(selector='td:nth-of-type(1) img', attr='alt')),
        Attr(name='author', func=parser.text(selector='td:nth-of-type(3)')),
        Attr(name='substances',
             func=parser.text(selector='td:nth-of-type(4)',
                              replacers='&', substitute=',',
                              regex='([A-z0-9\-]+\s*[A-z0-9\-*\s]*)')),
        Attr(name='date', func=parser.text(selector='td:nth-of-type(5)')),
        Attr(name='views', func=parser.text(selector='td:nth-of-type(6)'))
    )
)

drug_report = Model(
    source=report_source,
    name='drug_report', selector='',
    database = MongoDB('erowid'),
    table='drug_report',
    attrs=(
        Attr(name='text', func=parser.text(selector='.report-text-surround')),
        Attr(name='weight', func=parser.text(selector='td.bodyweight-amount')),
    )
)

erowid = Scraper(
    name='erowid',
    num_getters=1, models=[report_listing, drug_report])
erowid.start()
