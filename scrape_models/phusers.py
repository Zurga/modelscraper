import dispatcher
import re


marktplaats = ScrapeModel(name='pornhub', domain='pornhub.com', num_getters=6, cookies={'CookieOptIn': 'true'},
                          phases=[
    Phase(
        getters=[
            Getter(url='http://www.pornhub.com/user/search?ageControl=1&username=&city=&gender=0&orientation=0&relation=0&country=&o=popular&age1=18&age2=99')
        ],
        templates=[
            Template(name='person', selector='.search-results',
                       attrs=[
                           Attr(name='url', selector='.usernameLink',
                                parse_func=sel_attr, func_kws={'attr': 'href'}),
                       ], getter=Getter(suffix='/subscriptions')),
            ]),
    Phase(templates=[
        Template(name='user',
                        store=StoreObject(
                            store_func=store_mongo, func_kws={'db': 'pornhub', 'collection': 'users'}),
                        attrs=[
                            Attr(name='url', selector='.profileUserName', parse_func=sel_attr,
                                        func_kws={'attr': 'href'})
                        ])
        Template(name='subscription', selector='.userWidgetWrapperGrid',
                        attrs=[
                            Attr(name='urls', selector='.userLink',
                                         parse_func=sel_attr, func_kws={'attr': 'href'}),
                        ], store=StoreObject(store_func=store_mongo,
                                                    func_kws={'db': 'pornhub', 'collection': 'users',
                                                              'query':

                        )
    ])

        ]
        )

disp = dispatcher.Dispatcher()
disp.add_scraper(marktplaats)

disp.run()
