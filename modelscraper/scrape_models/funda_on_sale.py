import models
from dispatcher import Dispatcher

types = ['woonhuis', 'appartement']

funda = models.ScrapeModel(name='funda.nl', domain='http://funda.nl', num_sources=2, runs=[
    models.Run(sources=[models.Source(url='http://funda.nl/koop/amsterdam/'+t+'/') for
                        t in types],
        templates=[
            models.Template(name='house', selector='.search-result', db_type='mongo_db',
                            db='funda', table='on_sale1',
                       attrs=[
                models.Attr(name='price', selector='.search-result-price', func='sel_text',
                            kws={'numbers': True}),
                models.Attr(name='street', selector='.search-result-title', func='sel_text'),
                models.Attr(name='realtor', selector='.realtor', func='sel_text'),
                models.Attr(name='rooms', selector='.search-result-info', func='sel_text',
                            kws={'regex': '(\d+) kamers', 'numbers': True}),
                models.Attr(name='zip', selector='.search-result-subtitle', func='sel_text', kws={'regex': '(\d{4} \w{2})'}),
                models.Attr(name='city', selector='.search-result-subtitle', func='sel_text', kws={'regex': '\d{4} \w{2} (\w+)'}),
                models.Attr(name='living_area', selector='.search-result-info span[title="Woonoppervlakte"]', func='sel_text',
                            kws={'regex': '(\d+)', 'numbers': True}),
                models.Attr(name='url', selector='.search-result-header a', func='sel_attr', kws={'attr': 'href'}),
            ]),
            models.Template(selector='.pagination', attrs=[
                models.Attr(name='url', selector='a', func='sel_attr', kws={'attr': 'href'},
                        source=models.Source())])
        ])
])

disp = Dispatcher()
disp.add_scraper(funda)
disp.run()
