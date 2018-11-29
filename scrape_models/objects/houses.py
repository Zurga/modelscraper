from modelscraper import Model, Attr


url = Attr('url')
contract = Attr('contract')
construction_type = Attr('construction_type')
surface = Attr('surface')
rooms = Attr('rooms')
place = Attr('place')
lat = Attr('lat')
lon = Attr('lon')
price = Attr('price')
offer_id = Attr('offer_id')
offer_type = Attr('offer_type')

house = Model(
    definition=True,
    name='offer',
    dated=True,
    attrs=[
        url,
        contract,
        construction_type,
        surface,
        rooms,
        place,
        price,
        offer_id,
        lat,
        lon,
        offer_type,
    ]
)
