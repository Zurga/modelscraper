from dispatcher import Dispatcher
import re
from components import ScrapeModel, Phase, Template, Attr, Source
from workers import WebSource
from parsers import HTMLParser


pornstars = ScrapeModel(
    name='pornhub_pornstars', domain='http://pornhub.com', num_getters=2,
    phases=[
        Phase(source_worker=WebSource, parser=HTMLParser, sources=[
            Source(url='http://www.pornhub.com/pornstars?o=a')],
                templates=[
                    Template(name='alphabet',
                                selector='.alphabetFilter .dropdownWrapper li',
                                attrs=[
                                    Attr(name='url', selector='a', func='sel_url',
                                    source=Source(active=False))
                                    ])
                ]),
        Phase(source_worker=WebSource, parser=HTMLParser, templates=[
            Template(name='pornstar', selector='.pornstarIndex li', db_type='MongoDB',
                    db='pornstars', collection='ranking', attrs=[
                        Attr(name='name', selector='.title', func='sel_text'),
                        Attr(name='rank', selector='.rank_number',
                             func='sel_text', kws={'numbers': True}),

                        Attr(name='views', selector='.pstarViews',
                             func='sel_text', kws={'numbers': True}),

                        Attr(name='videos', selector='.videosNumber',
                             func='sel_text', kws={'numbers': True}),

                        Attr(name='url', selector='a.title', func='sel_url'),
                        Attr(name='image_url', selector='img',
                             func='sel_attr', kws={'attr': 'src'}),
                    ]),
            Template(name='next_urls', selector='.pagination3', attrs=[
                Attr(name='url', selector='a', func='sel_url', source=Source())
            ])
        ])
    ])

dis = Dispatcher()
dis.add_scraper(pornstars)
dis.run()
