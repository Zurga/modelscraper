from modelscraper import Scraper, WebSource, MongoDB, HTMLParser, Model, Attr,\
    ORCSSSelector
from scrape_models.objects.estate_agents import name, website, \
    contact_persons, address, postal_code, city, phone_number, carte_number,\
    siret, rating, amount_renting, amount_selling, activities, \
    country, estate_agent


search = 'https://www.fnaim.fr/43-agences.htm?autocomplete=&AGB_NOM=&ACTIVITE%5B%5D=10&ACTIVITE%5B%5D=5&ACTIVITE%5B%5D=1&ACTIVITE%5B%5D=2&ACTIVITE%5B%5D=3&ACTIVITE%5B%5D=4&ACTIVITE%5B%5D=6&ACTIVITE%5B%5D=7&ACTIVITE%5B%5D=8&ACTIVITE%5B%5D=11&ACTIVITE%5B%5D=12&ACTIVITE%5B%5D=13&ACTIVITE%5B%5D=14&ACTIVITE%5B%5D=15&Find=Valider&idtf=43&op=AGB_NOM+asc&cp=&mp=10'
agence_test_url = 'https://www.fnaim.fr/agence-immobiliere/21370/43-ste-genevieve-des-bois-agence-adu-donjon-agence-du-donjon-agence-a-du-moulin-gestion.htm'
list_source = WebSource(name='list_source', urls=[search], time_out=2)
agent_source = WebSource(name='agent_source', session=list_source.session,
                         time_out=2, test_urls=agence_test_url)
db = MongoDB(db='estate_agents')
htmlparser = HTMLParser()

next_page = Model(
    name='next_page',
    source=list_source,
    selector=htmlparser.select('.regletteNavigation a'),
    debug=True,
    attrs=[Attr(name='url', func=htmlparser.url(), emits=list_source)]
)

agent_url = Model(
    database=db, table='fnaim_agence_urls',
    name='agent_url',
    source=list_source,
    selector=htmlparser.select('li.item'),
    attrs=[
        Attr(name='url', func=htmlparser.url('h3 a'), emits=agent_source)
    ]
)

contact_persons_selector = ORCSSSelector(
    'ul.representant li', '//label[contains(text(), "Repr")]/..')

htmlparser = HTMLParser()
fnaim = estate_agent(
    source=agent_source,
    database=db, table='fnaim',
    selector=htmlparser.select('.agence_fiche'),
    required=True,
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
    ]
)
scraper = Scraper(models=[agent_url, next_page, fnaim])
