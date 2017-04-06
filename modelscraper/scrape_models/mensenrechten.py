from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


mensen = models.ScrapeModel(name='mensenrechten.nl', domain='http://mensenrechten.nl', num_getters=2, runs=[
    models.Run(source_worker=WebSource, parser=HTMLParser, sources=[
        models.Source(url="http://mensenrechten.nl/publicaties/oordelen")],
        templates=[
            models.Template(
                name='ground', selector='.aside',
                attrs=[
                    models.Attr(name='ground', selector='.gronden-checkbox', func='sel_attr',
                                kws={'attr': 'value'}, source={'active': False,
                                        'src_template': 'http://mensenrechten.nl/publicaties/oordelen?grond={}'}),
                ])
        ]),
    models.Run(source_worker=WebSource, parser=HTMLParser,
        templates=[
            models.Template(name='verdict_url', selector='.section .article',
                            attrs=[
                    models.Attr(name='url', selector='a.teaser-readmore', func='sel_url',
                                source={'active': False, 'src_template': '{}/detail'}),
                ]
            ),
            models.Template(name='next_page', selector='.pager-next',
                            attrs=[
                    models.Attr(name='next_url', selector='a', func='sel_url',
                                source=True)
                            ]),
        ]),
    models.Run(source_worker=WebSource, parser=HTMLParser, templates=[
            models.Template(name='verdict', selector='.section', db_type='mongo_db', db='human_rights',
               table='verdicts', attrs=[
                models.Attr(name='title', selector='.header-medium', func='sel_url'),
                models.Attr(name='verdict', selector='.oordelen-page .content p', func='sel_url'),
                models.Attr(name='ground', selector='tag-link a[href*="grond"]', func='sel_url'),
                models.Attr(name='terrain', selector='tag-link a[href*="terrein"]', func='sel_url'),
                models.Attr(name='keywords', selector='tag-link a[href*="trefwoord"]', func='sel_url'),
                models.Attr(name='law_articles', selector='tag-link a[href*="wetsverwijzing"]', func='sel_url'),
                models.Attr(name='dictum', selector='tag-link a[href*="dictum"]', func='sel_url'),
            ])
        ])
]
)

disp = Dispatcher()
disp.add_scraper(mensen)
disp.run()
