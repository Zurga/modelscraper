import dispatcher
import models
from functions.store_functions import *
from functions.parse_functions import *


goudengids = ScrapeModel(
    name='goudengids', domain='http://www.detelefoongids.nl', num_getters=4,
    phases=[
        Phase(
            getters=[Getter(url='http://www.detelefoongids.nl/bedrijven/2-1/')],
            templates=[
                Template(
                    name='categories', selector='.categories-container',
                    attrs=[
                        Attr(
                            name='category', selector='li a', func=sel_attr,
                            kws={'attr': 'href'}, getter={'active':False}),
                    ]
                )]),
        Phase(
            templates=[
                Template(
                    name='last_names', selector='.bulletList',
                    attrs=[
                        Attr(
                            name='letter', selector='li a[href*="amsterdam"]', func=sel_attr,
                            kws={'attr': 'href'}, getter={'active':False}),
                    ],
                ),
            ]
        ),
        Phase(
            templates=[
                Template(
                    name='person', selector='.business',
                    attrs=[
                        Attr(
                            name='name', selector='span[itemprop="name"]',
                            func=sel_text),
                        Attr(
                            name='number', selector='span[itemprop="telephone"]', func=sel_text),
                        Attr(
                            name='street', selector='p[itemprop="streetAddress"]',
                            func=sel_text),
                        Attr(
                            name='zip', selector='p[itemprop="postalCode"]',
                            func=sel_text),
                        Attr(
                            name='street', selector='p[itemprop="addressRegion"]',
                            func=sel_text),
                        Attr(name='website', selector='li.website a',
                                    func=sel_attr, kws={'attr': 'href'})
                    ], store=StoreObject(func=store_mongo, kws={'db': 'businesses', 'collection': 'business'})
                ),
                Template(name='pagination', selector='#pagination', attrs=[
                    Attr(name='link', selector='li a', func=sel_attr,
                                kws={'attr': 'href'})


            ]
        )
    ]
    )
]
)
disp = dispatcher.Dispatcher()
disp.add_scraper(goudengids)
disp.run()

