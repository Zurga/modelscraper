from modelscraper import Scraper, WebSource, MongoDB, JSONParser, HTMLParser,\
    ORCSSSelector, Attr, Model
from scrape_models.objects.houses import url, contract, construction_type, \
    surface, rooms, place, lat, lon, price, offer_id, offer_type, house

from scrape_models.objects.estate_agents import website, name, \
    contact_persons, address, postal_code, city, country, phone_number, \
    carte_number, siret, rating, amount_renting, \
    amount_selling, activities, estate_agent


db = MongoDB(db='fnaim')
parser = JSONParser()
htmlparser = HTMLParser()
regions = list(range(100))
params = '&'.join(keys + '%0d' % reg
                  for reg, keys in zip(regions, ['keys[]='] * len(regions)))

js_url = 'https://www.fnaim.fr/include/ajax/annonce/ajax.annonceItemsJson.php'
fnaim_source = WebSource(urls=[js_url, js_url], func='get',
                         # params=['&'.join([params, 'idTransaction=1']),
                         #        '&'.join([params, 'idTransaction=2'])],
                         test_urls=[js_url + '?keys[]=75106&idTransaction=1'],
                         debug=True,
                         )

annonce_source = WebSource(
    url_template='https://www.fnaim.fr/include/ajax/annonce/ajax.annonce.php',
    kwargs_format={'params': ['offer_id', 'offer_type']},
    params='id={offer_id}&type={offer_type}', func='get',
    debug=True, session=fnaim_source.session)

estate_agent_source = WebSource(session=fnaim_source.session, debug=True)

offer = house(
    source=fnaim_source,
    selector=parser.select('.[]|.values|.[]'),
    attrs=[
        url(func=parser.text('.params.href',
                             template='https://www.fnaim.fr{}')),
        contract(func=parser.text('.params.href',
                                  regex='\/\d+-(\w+)')),
        construction_type(func=parser.text('.params.href',
                                           regex='\/\d+-\w+-(\w+)')),
        surface(func=parser.text(
            '.params.title', regex='(\d+)m²', numbers=True)),
        rooms(func=parser.text('.params.title', regex='(\d+) pièce\(s\)')),
        place(func=parser.text('.lieu')),
        lat(func=parser.text('.lat')),
        lon(func=parser.text('.lng')),
        price(func=parser.text('.params.iconParam.iconUrl', numbers=True)),
        offer_id(func=parser.text('.params.id'),
                 emits=annonce_source),
        offer_type(func=parser.text('.params.type'))
    ],
    database=db, table='offers',
    )

contact_persons_selector = ORCSSSelector(
    'ul.representant li', '//label[contains(text(), "Repr")]/..')

mini_offer = Model(
    source=annonce_source,
    name='mini_offer',
    debug=True,
    attrs=[
        url(func=htmlparser.url('.lien_agence.info_agence'),
            emits=estate_agent_source)
    ]
)

estate_agent = estate_agent(
    source=estate_agent_source,
    database=db, table='estate_agents',
    attrs=[
        website(func=htmlparser.url('a.site.external')),
        name(func=htmlparser.text('h1')),
        contact_persons(func=htmlparser.text(contact_persons_selector)),
        address(func=htmlparser.text('.lieu', regex='(.*)\d{5}')),
        postal_code(func=htmlparser.text('.lieu', regex='\d{5}')),
        city(func=htmlparser.text('.lieu', regex='\d{5} (\w+)')),
        country(value='France'),
        phone_number(func=htmlparser.text('#agence_call', numbers=True)),
        carte_number(
            func=htmlparser.text('//label[contains(text(),"Carte N°")]/..')),
        siret(func=htmlparser.text('//li/label[contains(text(),"SIRET")]/..',
                                   numbers=True)),
        rating,
        amount_renting(func=htmlparser.text('.activite a',
                                            regex='(\d+)\s*biens* en location')
                       ),
        amount_selling(func=htmlparser.text('.activite a',
                                            regex='(\d+)\s*biens* en vente')),
        activities(func=htmlparser.text('.caracteristique.tab-right.txt li')),
    ])

fnaim = Scraper(models=[offer, estate_agent, mini_offer])

if __name__ == "__main__":
    fnaim.start()
