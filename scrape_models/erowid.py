from modelscraper.components import Scraper, Template, Attr
from modelscraper.sources import WebSource
from modelscraper.databases import MongoDB

list_url = "https://www.erowid.org/experiences/exp.cgi?ShowViews=1&Cellar=0&Start=0&Max=1"
listing_source = WebSource(name='listing', urls=[list_url], domain='https://www.erowid.org/experiences/')
report_source = WebSource()
transfer_attr = Attr(transfers=True)

report_listing = Template(
    source=listing_source,
    name='report_url', selector='.exp-list-table tr',
    emits=report_source,
    attrs=(
        Attr(name='url', selector='td:nth-of-type(2) a', func='sel_url'),
        Attr(name='title', selector='td:nth-of-type(2) a', func='sel_text'),
        Attr(name='rating', selector='td:nth-of-type(1) img', func='sel_attr',
             kws={'attr': 'alt'}),
        Attr(name='author', selector='td:nth-of-type(3)', func='sel_text'),
        Attr(name='substances', selector='td:nth-of-type(4)', func='sel_text',
             kws={'replacers': '&', 'substitute': ',', 'regex':
                  '([A-z0-9\-]+\s*[A-z0-9\-*\s]*)'}),
        Attr(name='date', selector='td:nth-of-type(5)', func='sel_text'),
        Attr(name='views', selector='td:nth-of-type(6)', func='sel_text')
    )
)

drug_report = Template(
    source=report_source,
    name='drug_report', selector='',
    database = MongoDB('erowid'),
    table='drug_report',
    attrs=(
        Attr(name='text', selector='.report-text-surround', func='sel_text'),
        Attr(name='weight', selector='td.bodyweight-amount', func='sel_text'),
    )
)

erowid = Scraper(
    name='erowid',
    num_getters=1, templates=[report_listing, drug_report])
erowid.start()
