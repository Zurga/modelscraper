from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient
import operator as op

data = 'utf8=%E2%9C%93&authenticity_token=PjYYz7Xn2bU%2BfsnFSUNlPKXKEnltYT%2BtkI4cjlXOU6EBEk2i%2FXjjmj9erEMDWPQLd1KQ7biu8vhyoy%2BG9J%2F8rA%3D%3D&user%5Bemail%5D=jim.lemmers%40gmail.com&user%5Bpassword%5D=drstatistisch&commit=Log+in'

drstat = ScrapeModel(
    name='namen', domain='http://drstat.net/', num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://drstat.net/nl/session",
                      attrs=(Attr(name='user[email]',
                                         value='jim.lemmers@gmail.com'),
                             Attr(name='user[password]',
                                         value='drstatistisch'),
                             Attr(name='utf8', value='✓'),
                             Attr(name='commit', value='Log+in'),
                             ),
                      )
                        ],
        templates=[
            Template(
                selector='#new_user', source={'method': 'post',
                                              'url': "http://drstat.net/nl/session",
                                              'parse': False,
                                              },
                attrs=[
                    Attr(name='authenticity_token',
                                selector='input[name="authenticity_token"]',
                                func='sel_attr', kws={'attr': 'value'})
                ],
            )
    ]),
    Phase(source_worker=WebSource, sources=[
        Source(url="http://www.drstat.net/nl/modules")],
        templates=[
            Template(
                name='module', selector='.module',
                attrs=[
                    Attr(name='next', selector='h3 a',  func='sel_attr',
                                kws={'attr': 'href'}, source={'active': False}),
                ])
            ]
    ),
    Phase(source_worker=WebSource,
        templates=[
            Template(
                name='course', selector='', func='update',
                kws={'key': 'name', 'method': '$addToSet'},
                db_type='mongo_db', db='drstat', table='courses',
                attrs=[
                    Attr(name='name', selector='li.title',
                                func='sel_text'),

                    Attr(name='text', selector='#bsocontent p',
                                func='sel_text', kws={'as_list': True}),
                ]
            ),
            Template(
                name='next_url', selector='div.next',
                attrs=[
                    Attr(name='next', selector='a', func='sel_attr',
                                kws={'attr': 'href'}, source=True)
                ]
            )
        ]
    )
    ]
)

d = Dispatcher()
d.add_scraper(drstat)
d.run()
