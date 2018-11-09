from modelscraper.components import Scraper, Model, Attr
from modelscraper.sources import WebSource, FileSource
from modelscraper.parsers import JSONParser
from modelscraper.databases import MongoDB
from .objects.products import product, product_name, price, nutrition,\
    brand_name, unitsize, availability, store_id, category, ingredients

from string import ascii_lowercase

base_search = 'service/rest/delegate?url=/zoeken?rq={}&searchType=product'
delegate_url = 'https://www.ah.nl/service/rest/delegate?url={}'
table_trans = str.maketrans('[]', '<>')
translate_table = lambda text: text.translate(table_trans)

search = WebSource(name='search',
                   url_template='https://www.ah.nl/{}',
                   urls=(base_search.format(l) for l in ascii_lowercase))

product_test = 'producten/product/wi238928/ah-biologisch-schouderkarbonade'
product_source = WebSource(name='product_source', url_template=delegate_url,
                           test_urls=[product_test])
db = MongoDB(db='ah_nl')
parser = JSONParser()

url = Attr(name='url', func=parser.text(selector='navItem/link/href'))

search_template = Model(
    source=search, name='search_result',
    selector=parser.select('//type[text() = "SearchLane"]/../_embedded/items'),
    attrs=[url(emits=product_source)]
)

load_more_template = Model(
    source=search,
    name='load_more',
    selector=parser.select('//type[text() = "LoadMoreLane"]/..'),
    attrs=[url(emits=search)]
)

product_selector = '//type[text() = "ProductDetailLane"]/..//type[text() = "Product"]/..'
paragraph_selector = '//content//title[text() = "{}"]/../../../content[last()]/text/body'
product = product(
    source=product_source,
    name='product',
    table='products',
    database=db,
    attrs=[
        nutrition(
            func=[parser.text(selector=paragraph_selector.format('Voedingswaarden')),
                  parser.custom_func(function=translate_table),
                  parser.table()],
        ),
        ingredients(func=parser.text(selector=paragraph_selector.format("Ingrediënten"))),
        product_name(func=parser.text(selector=product_selector + '//description')),
        brand_name(func=parser.text(selector=product_selector + '//brandName')),
        unitsize(func=parser.text(selector=product_selector + '//unitSize')),
        availability(func=parser.text(
            selector=product_selector + '//availability/orderable')),
        price(func=parser.text(selector=product_selector + '//priceLabel/now')),
        store_id(func=parser.text(selector=product_selector + '//id')),
        category(func=parser.text(selector=product_selector + '//categoryName')),
        Attr(name='url', from_source=True)
        ]
)

ah = Scraper(
    name='ah', domain='https://www.ah.nl/', logfile='ah_nl',
    models=[search_template, load_more_template, product]
)
