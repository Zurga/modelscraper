import dispatcher
import models
from functions.store_functions import *
from functions.parse_functions import *


goudengids = models.ScrapeModel(
    name='goudengids', domain='http://www.detelefoongids.nl', num_getters=4,
    runs=[
        models.Run(
            getters=[models.Getter(url='http://www.detelefoongids.nl/bedrijven/2-1/')],
            templates=[
                models.Template(
                    name='categories', selector='.categories-container',
                    attrs=[
                        models.Attr(
                            name='category', selector='li a', func=sel_attr,
                            kws={'attr': 'href'}, getter={'active':False}),
                    ]
                )]),
        models.Run(
            templates=[
                models.Template(
                    name='last_names', selector='.bulletList',
                    attrs=[
                        models.Attr(
                            name='letter', selector='li a[href*="amsterdam"]', func=sel_attr,
                            kws={'attr': 'href'}, getter={'active':False}),
                    ],
                ),
            ]
        ),
        models.Run(
            templates=[
                models.Template(
                    name='person', selector='.business',
                    attrs=[
                        models.Attr(
                            name='name', selector='span[itemprop="name"]',
                            func=sel_text),
                        models.Attr(
                            name='number', selector='span[itemprop="telephone"]', func=sel_text),
                        models.Attr(
                            name='street', selector='p[itemprop="streetAddress"]',
                            func=sel_text),
                        models.Attr(
                            name='zip', selector='p[itemprop="postalCode"]',
                            func=sel_text),
                        models.Attr(
                            name='street', selector='p[itemprop="addressRegion"]',
                            func=sel_text),
                        models.Attr(name='website', selector='li.website a',
                                    func=sel_attr, kws={'attr': 'href'})
                    ], store=models.StoreObject(func=store_mongo, kws={'db': 'businesses', 'collection': 'business'})
                ),
                models.Template(name='pagination', selector='#pagination', attrs=[
                    models.Attr(name='link', selector='li a', func=sel_attr,
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

