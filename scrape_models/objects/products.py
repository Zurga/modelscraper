from modelscraper.components import Attr, Model

product_name = Attr(name='product_name')
price = Attr(name='price')
nutrition = Attr(name='nutrition')
brand_name = Attr(name='brand_name')
unitsize = Attr(name='unitsize')
availability = Attr(name='availability')
store_id = Attr(name='store_id')
category = Attr(name='category')
ingredients = Attr(name='ingredients')
url = Attr(name='url')

product = Model(
    name='product',
    definition=True,
    attrs=[url, product_name, price, nutrition, brand_name, unitsize, availability,
           store_id, category, ingredients])
