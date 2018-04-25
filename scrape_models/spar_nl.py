from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import HTMLParser, JSONParser
from .objects.products import product_name, price, nutrition


cookie = {'visitor':{
    "Cart":{"Created":"2018-02-07T00:06:05.7108646+01:00","Id":None,"OrderSelectionType":None,"SelectedShippingAddressNumber":None},
    "Wishlist":{"Products":[]},
    "FirstVisit":"2016-02-07T00:00:00.7108646+01:00",
    # "SelectedStore":{"StoreId":27,"StoreReferenceKey":384},
    "SelectedStore":{"StoreId":207,"StoreReferenceKey":493},
    "HasSelectedStore":True,"AcceptedCookies":None,"LastViewedProducts":None}}

menu_template = Template(name='menu', attrs=[
    Attr(name='menu_item', selector='.c-category-tile__item', func='sel_url',
         source={'active': False, 'src_template':'{}?ppp=72'})
])

productmenu_template = Template(
    name='submenu', selector='.c-product-tile',
    attrs=[
    Attr(name='submenu_item', selector='.c-product-tile__meta > a',
         func='sel_url', source={'active': False}),
    Attr(name='pagination_item', selector='li.is-nexy > a', source=True)
    ])

product_name = product_name(selector='.c-offer__title')
price = price(selector='div.c-offer__price')
nutrition = nutrition(selector='.c-offer__nutrition table td')

product = Template(
    name='product',
    db='foods',
    table='spar2',
    db_type='MongoDB',
    attrs=[product_name, price, nutrition])

spar = ScrapeModel(
    name='spar.nl', cookie=cookie, domain='https://spar.nl', phases=[
        Phase(
            sources=(Source(url='https://spar.nl/boodschappen/'),),
            templates=[menu_template]),
        Phase(templates=[productmenu_template]),
        Phase(templates=[product])
    ])
