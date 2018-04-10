from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import JSONParser
from .objects.products import product_name, price, nutrition, brand_name,\
    unitsize, availability, store_id, category

import string


base_search = 'https://www.ah.nl/service/rest/delegate?url=/zoeken?rq={}&searchType=product'
base_url = 'https://www.ah.nl/{}'
delegate_url = 'https://www.ah.nl/service/rest/delegate?url={}'
search = (Source(url=base_search.format(l)) for l in string.ascii_lowercase)

product_selector = ['type:ProductDetailLane', '_embedded', 'items',
                    0, '_embedded','product']

product = Template(
    name='product',
    db='ah_nl',
    table='products',
    selector=['_embedded', 'lanes', '*'],
    attrs=[
        nutrition(func='sel_text',
            selector=[8, '_embedded', 'items', 1,'_embedded','sections',0,
                      '_embedded', 'content', 2, 'text', 'body']),

        product_name(selector=product_selector + ['description']),
        brand_name(selector=product_selector + ['brandName']),
        unitsize(selector=product_selector + ['unitSize']),
        availability(func='sel_value',
                     selector=product_selector + ['availability', 'orderable']),
        price(func='sel_value',
              selector=product_selector + ['priceLabel', 'now']),
        store_id(selector=product_selector + ['id']),
        category(selector=product_selector + ['categoryName']),
        ]
)

product_url = Attr(
    name='url',
    selector=['navItem', 'link', 'href'],
    func='sel_text',
    kws={'template': delegate_url},
    source={'active': False}
)

search_template = Template(
    name='search_result',
    db_type='MongoDB',
    db='ah_nl',
    table='product_urls',
    selector=['_embedded', 'lanes', 'type:SearchLane', '_embedded', 'items'],
    attrs=[product_url]
)

load_more = Attr(
    name='load_more_url',
    selector=['navItem', 'link', 'href'],
    func='sel_text',
    source=Source(src_template='https://www.ah.nl/{}')
)

load_more_template = Template(
    name='load_more',
    selector=['_embedded', 'lanes', 7],
    attrs=[load_more]
)


ah = ScrapeModel(
    name='ah', domain='https://www.ah.nl/',
    phases=[
        Phase(parser=JSONParser, sources=search,
              templates=[search_template, load_more_template]),
        Phase(parser=JSONParser, templates=[product])
    ]
)