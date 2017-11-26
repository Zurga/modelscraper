from components import *  # noqa
from parse_functions import *  # noqa
from store_functions import *  # noqa
from get_functions import *  # noqa
from dispatcher import Dispatcher


funda = ScrapeModel(name='funda.nl', domain='http://funda.nl', phases=[
    Phase(to_getter=[Getter(url='http://www.funda.nl/koop/verkocht/')],
        objects=[
            HTMLObject(name='house', selector='ul.object-list li.sold', store_func=store_mongo, kwargs={'db': 'funda', 'collection': 'sold'},
                       attrs=[
                Attr(name='price', selector='.price-wrapper .price', parse_func=sel_text),
                Attr(name='street', selector='.object-street', parse_func=sel_text),
                Attr(name='date_sold', selector='.price-wrapper .date', parse_func=sel_text),
                Attr(name='realtor', selector='.realtor', parse_func=sel_text),
                Attr(name='realtor_url', selector='.realtor', parse_func=sel_attr, kwargs={'attr': 'href'}),
                Attr(name='rooms', selector='span[title="Aantal kamers"]', parse_func=sel_text),
                Attr(name='address', selector='.properties-list li:nth-of-type(1)', parse_func=sel_text),
                Attr(name='living_area', selector='.properties-list span[title="Woonoppervlakte"]', parse_func=sel_text),
                Attr(name='total_area', selector='.properties-list span[title="Perceeloppervlakte"]', parse_func=sel_text),
                           Attr(name='url', selector='.object-street', parse_func=sel_attr, kwargs={'attr': 'href'}),
            ])
            ,
            HTMLObject(name='next_page', attrs=[
                Attr(name='next_link', selector='.next', parse_func=sel_attr, kwargs={'attr': 'href'},
                     follow=Follow(func=get_urls))
            ])
        ])
    ])

disp = Dispatcher([funda])
disp.run()
