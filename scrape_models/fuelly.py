from modelscraper.components import ScrapeModel, Template, Attr
from modelscraper.sources import WebSource
import string


motorcycles = Source(urls=["http://www.fuelly.com/motorcycle"])
vehicle_source = WebSource()

vehicle_link = Template(
    source=motorcycles,
    name='vehicle_link', selector='.list li',
    attrs=[
        Attr(name='amount',func='sel_text',
             kws={'regex': '\((\d+)\)', 'debug': True, 'numbers': True }),
        Attr(name='url', selector='a',
             func='sel_url', emits=vehicle_source,
             source_condition={'amount': '> 2'}),
    ]
)

vehicle = Template(
    source=vehicle_source,
    name='vehicle', selector='.model-year-item',
    db_type='MongoDB', db='fuelly', table='motorcycles',
    attrs=[
        Attr(name='name', selector='.summary-view-all-link a',
                    func='sel_text'),
        Attr(name='url', selector='.summary-view-all-link a',
                    func='sel_url'),
        Attr(name='year', selector='.summary-year',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='avg', selector='.summary-avg-data',
                    func='sel_text'),
        Attr(name='total_motorcycles', selector='.summary-total',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='total_fuelups', selector='.summary-fuelups',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='total_miles', selector='.summary-miles',
                    func='sel_text', kws={'numbers': True}),
    ]
)

fuelly = ScrapeModel(
    name='fuelly', domain='http://www.fuelly.com', num_getters=1,
    templates=[vehicle_link, vehicle])
