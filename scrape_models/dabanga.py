from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


dabanga = ScrapeModel(
    name='dabanga', domain='https://www.dabangasudan.org/en', num_getters=2,
    phases=[
    Phase(sources=(
        Source(url="https://www.dabangasudan.org/en/all-news"),),
        templates=(
            Template(
                name='article_url', selector='.list-item.news-item-small',
                db_type='MongoDB', db='dabanga', table='article_urls',
                attrs=[
                    Attr(name='url', selector='a:nth-of-type(1)',
                         func='sel_url', source={'active': False}),
                ]
            ),
            Template(name='pagination', selector='.pager',
                     attrs=[
                         Attr(name='url', selector='a',
                              func='sel_url',
                              source=True),
                     ]),
            )
    ),
    Phase(synchronize=True,templates=[
            Template(
                name='article', selector='#content',
                db_type='MongoDB', db='dabanga', table='article',
                attrs=[
                    Attr(name='title', selector='h1',
                                func='sel_text'),
                    Attr(name='text', selector='.article .body-text',
                                func='sel_text'),
                    Attr(name='date', selector='.article .time',
                                func='sel_text'),
                    Attr(name='place', selector='.article .place',
                                func='sel_text'),
                    Attr(name='img', selector='.article img',
                                func='sel_attr', kws={'attr': 'src'}),
                ]
            ),
        ]
    )]
)

d = Dispatcher()
d.add_scraper(dabanga)
d.run()
