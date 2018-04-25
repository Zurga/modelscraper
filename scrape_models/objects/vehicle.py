from modelscraper.components import Template, Attr


vehicle_type = Attr(name='vehicle_type')
price = Attr(name='price', func='sel_text', kws={'numbers': True}, type=int)
brand = Attr(name='brand', func='sel_text')
make = Attr(name='make', func='sel_text')
year = Attr(name='year', func='sel_text', kws={'numbers': True}, type=int)
mileage = Attr(name='mileage', func='sel_text', kws={'numbers': True}, type=int)
url = Attr(name='url', func='sel_url')
power = Attr(name='power', func='sel_text')
usage = Attr(name='usage', func='sel_text')

vehicle = Template(
    name='vehicle',
    attrs=[
        vehicle_type,
        price,
        brand,
        make,
        year,
        mileage,
        url,
        power,
        usage,
    ]
)
