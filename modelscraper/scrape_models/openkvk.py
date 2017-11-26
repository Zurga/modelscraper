import dispatcher
import models
from functions.store_functions import *
from functions.parse_functions import *


kvk = ScrapeModel(name='kvk', domain='http://www.nationalebedrijvengids.nl', num_getters=10, phases=[
    Phase(getters=(models.Getter(url='http://www.nationalebedrijvengids.nl/bedrijf/{}'.format(i)) for i
                        in range(2500000, 3000001)),
            templates=[
                Template(
                    name='company', selector='.colmn.three-fifth',
                    attrs=[
                        Attr(name='name', selector='h1', func=sel_text),
                        Attr(name='website', selector='div.box:nth-of-type(3) a[href*="http"]', func=sel_attr,
                                    kws={'attr': 'href'}),
                        Attr(name='kvk', selector='div.box:nth-of-type(4) a[href*="http"]', func=sel_text),
                        Attr(name='sector', selector='.box.nav a[href*="sector"]', func=sel_text),
                    ], store=StoreObject(func=store_mongo, kws={'db': 'bedri', 'collection': 'companies'})
                ),
            ]
            )
        ],
    )

disp = dispatcher.Dispatcher()
disp.add_scraper(kvk)
disp.run()
