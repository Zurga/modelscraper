from modelscraper.components import Template, Attr

product_name = Attr(
    name='product_name',
    func='sel_text')

price = Attr(
    name='price',
    func='sel_text')

nutrition = Attr(
    name='nutrition',
    func='sel_table')

brand_name = Attr(
    name='brand_name',
    func='sel_text')

unitsize = Attr(
    name='unitsize',
    func='sel_text')

availability = Attr(
    name='availability',
    func='sel_text')

store_id = Attr(
    name='store_id',
    func='sel_text')

category = Attr(
    name='category',
    func='sel_text')

ingredients = Attr(
    name='ingredients',
    func='sel_text')
