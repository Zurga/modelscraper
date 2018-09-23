from modelscraper.components import Scraper, Template, Attr
from modelscraper.databases import MongoDB
from modelscraper.sources import WebSource
import string


vehicle_sources = WebSource(urls=["http://www.fuelly.com/motorcycle",
                              "http://www.fuelly.com/car"],
                        attrs=[{'type': 'motorcycle'}, {'type': 'car'}])
vehicle_source = WebSource()

vehicle_link = Template(
    source=vehicle_sources,
    name='vehicle_link', selector='.models-list li',
    attrs=[
        Attr(name='url', selector='a',
             func='sel_url', emits=vehicle_source),
        Attr(name='type', from_source=True, transfers=True)
    ]
)

database = MongoDB('fuelly_test')
vehicle = Template(
    source=vehicle_source,
    name='vehicle', selector='.model-year-item',
    database=database,
    table='vehicles',
    attrs=[
        Attr(name='name', selector='.summary-view-all-link a',
                    func='sel_text'),
        Attr(name='url', selector='.summary-view-all-link a',
                    func='sel_url'),
        Attr(name='year', selector='.summary-year',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='avg', selector='.summary-avg-data',
                    func='sel_text'),
        Attr(name='amount', selector='.summary-total',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='total_fuelups', selector='.summary-fuelups',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='total_miles', selector='.summary-miles',
                    func='sel_text', kws={'numbers': True}),
        Attr(name='type', from_source=True),
        Attr(name='amount', from_source=True)
    ]
)

fuelly = Scraper(
    name='fuelly', num_getters=1,
    templates=[vehicle_link, vehicle])
