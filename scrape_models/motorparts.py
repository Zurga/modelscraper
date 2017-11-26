from modelscraper.dispatcher import Dispatcher
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source

motorparts = ScrapeModel(
    name='motorparts', domain='http://www.2wheelpros.com',
    phases=[
        Phase(source_worker=WebSource, parser=HTMLParser, n_workers=2,
            sources=(Source(url='http://www.2wheelpros.com/oem-parts/'),),
            templates=(
                Template(name='brand',
                         selector='#nav > ul > li > a', attrs=(
                             Attr(name='url', func='sel_url',
                                  source={'active': False}),
                         ),),)
            ),
        Phase(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='year', selector='a.yearlink', attrs=(
                Attr(name='url', func='sel_url', source={'active': False}),)),),
          ),
        Phase(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='model', selector='a.modellink', attrs=(
                Attr(name='url', func='sel_url', source={'active': False}),
            )
            ),
        ),
        ),
        Phase(source_worker=WebSource, parser=HTMLParser, n_workers=2, templates=(
            Template(name='partCategory', db='motorparts',
                     table='part_categories', db_type='mongo_db',
                     selector='article.category',
                     attrs=(
                         Attr(name='url', func='sel_url',
                              selector='a:last-of-type',
                              source={'active':False, 'copy_attrs':
                                      {'url': 'category_url'}}),
                         Attr(name='name', func='sel_text',
                              selector='.description'),
                            )
            ),
            Template(name='motorcycle', db='motorparts',
                            table='motorcycles', db_type='mongo_db', attrs=(
                Attr(name='make', func='sel_text',
                            selector='#ctl00_cphMain_hHeadMake'),
                Attr(name='year', func='sel_text',
                            selector='#ctl00_cphMain_hHeadYear'),
                Attr(name='model', func='sel_text',
                    selector='.breadcrumbs li:last-of-type a'),
                Attr(name='part_category_urls',
                    selector='article.category a:last-of-type',
                    func='sel_url'),
            )),
            )
        ),
        Phase(source_worker=WebSource, parser=HTMLParser, n_workers=2, templates=(
            Template(name='part', selector='.scrollable-area-2 .cart-table tr',
                     db='motorparts', table='parts', db_type='mongo_db',
                     attrs=(
                         Attr(name='part_number', func='sel_text',
                              selector='h4 + span'),
                         Attr(name='amount', func='sel_text',
                              selector='.col-2 span:last-of-type'),
                         Attr(name='drawing_number', func='sel_text',
                              selector='.col-1 span'),
                         Attr(name='url', func='sel_url', selector='h4 a'),
                         Attr(name='name', func='sel_text', selector='h4 a'),
                     )),
        ))
])

disp = Dispatcher()
disp.add_scraper(motorparts)
disp.run()
