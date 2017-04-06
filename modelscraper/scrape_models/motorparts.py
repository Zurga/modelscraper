from dispatcher import Dispatcher
from workers import WebSource
from parsers import HTMLParser
from models import ScrapeModel, Run, Template, Attr, Source

motorparts = ScrapeModel(
    name='motorparts', domain='http://www.2wheelpros.com', num_sources=2,
    runs=[
        Run(source_worker=WebSource, parser=HTMLParser,
            sources=(Source(url='http://www.2wheelpros.com/oem-parts/'),),
            templates=(
                Template(name='brand',
                         selector='#nav > ul > li:nth-of-type(1) > a', attrs=(
                             Attr(name='url', func='sel_url',
                                  source={'active': False}),
                         ),),)
            ),
        Run(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='year', selector='.yearlink', attrs=(
                Attr(name='url', func='sel_url', source={'active': False}),)),),
          ),
        Run(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='model', selector='.modellink', attrs=(
                Attr(name='url', func='sel_url', source={'active': False}),
            )
            ),
        ),
        ),
        Run(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='partCategory', db='motorparts',
                     table='part_categories', source={'active':False,
                                                      'parent':True},
                     selector='.category',
                     attrs=(
                         Attr(name='url', func='sel_url',
                              selector='a:last-of-type'),
                         Attr(name='name', func='sel_text',
                              selector='.description'),
                            )
            ),
            Template(name='motorcycle', db='motorparts',
                            table='motorcycles', attrs=(
                Attr(name='make', func='sel_text',
                            selector='#ctl00_cphMain_hHeadMake'),
                Attr(name='year', func='sel_text',
                            selector='#ctl00_cphMain_hHeadYear'),
                Attr(name='model', func='sel_text',
                    selector='.breadcrumbs a:last-of-type'),
                Attr(name='part_category_urls',
                    selector='.category a:last-of-type',
                    func='sel_url'),
            )),
            )
        ),
        Run(source_worker=WebSource, parser=HTMLParser, templates=(
            Template(name='part', selector='.scrollable-area-2 .cart-table tr',
                     db='motorparts', table='parts', func='update',
                     attrs=(
                         Attr(name='part_number', func='sel_text',
                              selector='h4 + span'),
                         Attr(name='amount', func='sel_text',
                              selector='.col-2 span:last-of-type'),
                         Attr(name='drawing_number', func='sel_text',
                              selector='.col-1 span'),
                     )),
        ))
])

disp = Dispatcher()
disp.add_scraper(motorparts)
disp.run()
