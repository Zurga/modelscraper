import models
from dispatcher import Dispatcher

types = ['woonhuis', 'appartement']

funda = ScrapeModel(name='funda.nl', domain='http://funda.nl', num_sources=2, phases=[
    Phase(sources=[models.Source(url='http://funda.nl/koop/amsterdam/'+t+'/') for
                        t in types],
        templates=[
            Template(name='house', selector='.search-result', db_type='MongoDB',
                            db='funda', table='on_sale1',
                       attrs=[
                Attr(name='price', selector='.search-result-price', func='sel_text',
                            kws={'numbers': True}),
                Attr(name='street', selector='.search-result-title', func='sel_text'),
                Attr(name='realtor', selector='.realtor', func='sel_text'),
                Attr(name='rooms', selector='.search-result-info', func='sel_text',
                            kws={'regex': '(\d+) kamers', 'numbers': True}),
                Attr(name='zip', selector='.search-result-subtitle', func='sel_text', kws={'regex': '(\d{4} \w{2})'}),
                Attr(name='city', selector='.search-result-subtitle', func='sel_text', kws={'regex': '\d{4} \w{2} (\w+)'}),
                Attr(name='living_area', selector='.search-result-info span[title="Woonoppervlakte"]', func='sel_text',
                            kws={'regex': '(\d+)', 'numbers': True}),
                Attr(name='url', selector='.search-result-header a', func='sel_attr', kws={'attr': 'href'}),
            ]),
            Template(selector='.pagination', attrs=[
                Attr(name='url', selector='a', func='sel_attr', kws={'attr': 'href'},
                        source=Source())])
        ])
])

disp = Dispatcher()
disp.add_scraper(funda)
disp.run()
