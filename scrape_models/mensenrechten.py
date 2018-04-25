from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


mensen = ScrapeModel(name='mensenrechten.nl', domain='http://mensenrechten.nl', num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://mensenrechten.nl/publicaties/oordelen")],
        templates=[
            Template(
                name='ground', selector='.aside',
                attrs=[
                    Attr(name='ground', selector='.gronden-checkbox', func='sel_attr',
                                kws={'attr': 'value'}, source={'active': False,
                                        'src_template': 'http://mensenrechten.nl/publicaties/oordelen?grond={}'}),
                ])
        ]),
    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=[
            Template(name='verdict_url', selector='.section .article',
                            attrs=[
                    Attr(name='url', selector='a.teaser-readmore', func='sel_url',
                                source={'active': False, 'src_template': '{}/detail'}),
                ]
            ),
            Template(name='next_page', selector='.pager-next',
                            attrs=[
                    Attr(name='next_url', selector='a', func='sel_url',
                                source=True)
                            ]),
        ]),
    Phase(source_worker=WebSource, parser=HTMLParser, templates=[
            Template(name='verdict', selector='.section', db_type='MongoDB', db='human_rights',
               table='verdicts', attrs=[
                Attr(name='title', selector='.header-medium', func='sel_url'),
                Attr(name='verdict', selector='.oordelen-page .content p', func='sel_url'),
                Attr(name='ground', selector='tag-link a[href*="grond"]', func='sel_url'),
                Attr(name='terrain', selector='tag-link a[href*="terrein"]', func='sel_url'),
                Attr(name='keywords', selector='tag-link a[href*="trefwoord"]', func='sel_url'),
                Attr(name='law_articles', selector='tag-link a[href*="wetsverwijzing"]', func='sel_url'),
                Attr(name='dictum', selector='tag-link a[href*="dictum"]', func='sel_url'),
            ])
        ])
]
)

disp = Dispatcher()
disp.add_scraper(mensen)
disp.run()
