import dispatcher
import re


marktplaats = models.ScrapeModel(name='pornhub', domain='pornhub.com', num_getters=6, cookies={'CookieOptIn': 'true'},
                          runs=[
    models.Run(
        getters=[
            models.Getter(url='http://www.pornhub.com/user/search?ageControl=1&username=&city=&gender=0&orientation=0&relation=0&country=&o=popular&age1=18&age2=99')
        ],
        templates=[
            models.Template(name='person', selector='.search-results',
                       attrs=[
                           models.Attr(name='url', selector='.usernameLink',
                                parse_func=sel_attr, func_kws={'attr': 'href'}),
                       ], getter=Getter(suffix='/subscriptions')),
            ]),
    models.Run(templates=[
        models.Template(name='user',
                        store=models.StoreObject(
                            store_func=store_mongo, func_kws={'db': 'pornhub', 'collection': 'users'}),
                        attrs=[
                            models.Attr(name='url', selector='.profileUserName', parse_func=sel_attr,
                                        func_kws={'attr': 'href'})
                        ])
        models.Template(name='subscription', selector='.userWidgetWrapperGrid',
                        attrs=[
                            models.Attr(name='urls', selector='.userLink',
                                         parse_func=sel_attr, func_kws={'attr': 'href'}),
                        ], store=models.StoreObject(store_func=store_mongo,
                                                    func_kws={'db': 'pornhub', 'collection': 'users',
                                                              'query':

                        )
    ])

        ]
        )

disp = dispatcher.Dispatcher()
disp.add_scraper(marktplaats)

disp.run()
