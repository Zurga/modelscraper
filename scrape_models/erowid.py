from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


list_url = "https://www.erowid.org/experiences/exp.cgi?ShowViews=1&Cellar=0&Start=0&Max=24777"
erowid = ScrapeModel(
    name='erowid', domain='https://www.erowid.org/experiences/',
    num_getters=1, phases=[
    Phase(
        sources=[Source(url=list_url)],
        templates=(
            Template(
                name='report_url', selector='.exp-list-table tr',
                source=Source(active=False, copy_attrs=True),
                attrs=(
                    Attr(name='url', selector='td:nth-of-type(2) a',
                         func='sel_url'),

                    Attr(name='title', selector='td:nth-of-type(2) a',
                         func='sel_text'),

                    Attr(name='rating', selector='td:nth-of-type(1) img',
                         func='sel_attr', kws={'attr': 'alt'}),

                    Attr(name='author', selector='td:nth-of-type(3)',
                         func='sel_text'),

                    Attr(name='substances', selector='td:nth-of-type(4)',
                         func='sel_text',
                         kws={'replacers': '&', 'substitute': ',', 'regex':
                              '([A-z0-9\-]+\s*[A-z0-9\-*\s]*)'}),

                    Attr(name='date', selector='td:nth-of-type(5)', func='sel_text'),

                    Attr(name='views', selector='td:nth-of-type(6)',
                         func='sel_text'),
                )
            ),
        )
    ),

    Phase(
        templates=(
            Template(
                name='drug_report', selector='',
                db_type='MongoDB', db='erowid', table='drug_report',
                attrs=(
                    Attr(name='text', selector='.report-text-surround', func='sel_text'),
                    Attr(name='weight', selector='td.bodyweight-amount', func='sel_text'),
                )
            ),
        )
    ),
])
