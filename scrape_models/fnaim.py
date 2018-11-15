from modelscraper import Scraper, Model, Attr, WebSource, MongoDB,\
    HTMLParser


db = MongoDB(db='fnaim')
parser = HTMLParser()
fnaim_source = WebSource(urls=['https://www.fnaim.fr'],
                         test_urls=['https://www.fnaim.fr'])
offer_source = WebSource()
announces_source = WebSource(n_workers=5)

url = Attr(name='url', func=parser.url())

region_list = Model(
    source=fnaim_source,
    name='region_list',
    selector=parser.select('#localiteOffset a'),
    attrs=[url(emits=announces_source)])

announces = Model(
    source=announces_source,
    name='announces',
    selector=parser.select('.annonces li a'),
    attrs=[url(emits=offer_source)])

next_page = Model(
    source=fnaim_source,
    name='next_page',
    selector=parser.select('.regletteNavigation a'),
    attrs=[url(emits=announces_source)])

offer = Model(
    source=offer_source,
    name='offer',
    selector=parser.select('.item'),
    attrs=[
        Attr('contract', func=parser.text('title', regex='^(\w+)'),
             raw_data=True),
        Attr('constuction_type',
             func=parser.text('title', regex='^\w+ (\w+)'),
             raw_data=True),
        Attr('surface', func=parser.text('.surface b', numbers=True)),
        Attr('rooms', func=parser.text('.pieces b')),
        Attr('place', func=parser.text('.lieu')),
        Attr('price',
             func=parser.text('h4', numbers=True)),
        Attr('dpe', func=parser.text('#dpeValue'))
    ],
    database=db, table='offers',
    debug=True)

fnaim = Scraper(models=[region_list, announces, offer])

if __name__ == "__main__":
    fnaim.start()
