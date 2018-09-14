from modelscraper.components import ScrapeModel, Template, Attr
from modelscraper.sources import WebSource, FileSource
from modelscraper.parsers import JSONParser
from modelscraper.databases import MongoDB
from .objects.products import product_name, price, nutrition, brand_name,\
    unitsize, availability, store_id, category, ingredients

from string import ascii_lowercase

base_search = 'service/rest/delegate?url=/zoeken?rq={}&searchType=product'
delegate_url = 'https://www.ah.nl/service/rest/delegate?url={}'
table_trans = str.maketrans('[]', '<>')

search = WebSource(name='search',
                   url_template='https://www.ah.nl/{}',
                   urls=(base_search.format(l) for l in ascii_lowercase))
#more_results = WebSource(url_template='https://www.ah.nl/{}')

product_test = 'producten/product/wi238928/ah-biologisch-schouderkarbonade'
product_source = WebSource(name='product_source', url_template=delegate_url,
                           test_urls=[product_test])
test_product = FileSource(urls=['data/ah_nl/products.json'])
db = MongoDB(db='ah_nl')

search_template = Template(
    source=search,
    name='search_result',
    database=db,
    table='product_urls',
    selector='//type[text() = "SearchLane"]/../_embedded/items',
    parser=JSONParser,
    attrs=[
        Attr(
            name='url',
            selector='navItem/link/href',
            func='sel_text',
            emits=product_source
        )
    ]
)

load_more_template = Template(
    source=search,
    name='load_more',
    selector='//type[text() = "LoadMoreLane"]/..',
    parser=JSONParser,
    attrs=[
        Attr(
            name='url',
            selector='navItem/link/href',
            func='sel_text',
            emits=search)
    ]
)

product_selector = '//type[text() = "ProductDetailLane"]/..//type[text() = "Product"]/..'
paragraph_selector = '//content//title[text() = "{}"]/../../../content[last()]/text/body'
product = Template(
    source=product_source,
    name='product',
    table='products',
    database=db,
    parser=JSONParser,
    attrs=[
        nutrition(
            func=['sel_text', 'custom_func', 'sel_table'],
            kws=[{}, {'function': lambda text: text.translate(table_trans)},
                 {}],
            selector=paragraph_selector.format('Voedingswaarden'),
        ),
        ingredients(selector=paragraph_selector.format("Ingrediënten")),
        product_name(selector=product_selector + '//description'),
        brand_name(selector=product_selector + '//brandName'),
        unitsize(selector=product_selector + '//unitSize'),
        availability(selector=product_selector + '//availability/orderable'),
        price(selector=product_selector + '//priceLabel/now'),
        store_id(selector=product_selector + '//id'),
        category(selector=product_selector + '//categoryName'),
        Attr(name='url', from_source=True)
        ]
)

ah = ScrapeModel(
    name='ah', domain='https://www.ah.nl/',
    templates=[search_template, load_more_template, product]
)
