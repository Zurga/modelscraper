from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source

list_url = "https://www.erowid.org/experiences/exp.cgi?ShowViews=1&Cellar=0&Start=0&Max=24777"
listing_souce = WebSource(urls=[list_url], domain='https://www.erowid.org/experiences/')
report_source = WebSource(domain='https://www.erowid.org/experiences/')

report_listing = Template(
    source=listing_source,
    name='report_url', selector='.exp-list-table tr',
    emits=report_source,
    attrs=(
        base_attr(name='url', selector='td:nth-of-type(2) a', func='sel_url'),
        base_attr(name='title', selector='td:nth-of-type(2) a', func='sel_text'),
        base_attr(name='rating', selector='td:nth-of-type(1) img', func='sel_attr',
             kws={'attr': 'alt'}),
        base_attr(name='author', selector='td:nth-of-type(3)', func='sel_text'),
        base_attr(name='substances', selector='td:nth-of-type(4)', func='sel_text',
             kws={'replacers': '&', 'substitute': ',', 'regex':
                  '([A-z0-9\-]+\s*[A-z0-9\-*\s]*)'}),
        base_attr(name='date', selector='td:nth-of-type(5)', func='sel_text'),
        base_attr(name='views', selector='td:nth-of-type(6)', func='sel_text')
    )
)

drug_report = Template(
    source=report_source,
    name='drug_report', selector='',
    db_type='MongoDB', db='erowid', table='drug_report',
    attrs=(
        Attr(name='text', selector='.report-text-surround', func='sel_text'),
        Attr(name='weight', selector='td.bodyweight-amount', func='sel_text'),
    )
)

erowid = ScrapeModel(
    name='erowid',
    num_getters=1, templates=[report_listing, drug_report])
