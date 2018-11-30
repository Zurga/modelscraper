from modelscraper import Attr, Model


name = Attr(name='name')
website = Attr(name='website')
contact_persons = Attr(name='contact_names', multiple=True)
address = Attr(name='address')
postal_code = Attr(name='postal_code')
city = Attr(name='city')
phone_number = Attr(name='phone')
carte_number = Attr(name='carte_number')
siret = Attr(name='siret')
rating = Attr(name='rating')
amount_renting = Attr(name='amount_renting')
amount_selling = Attr(name='amount_selling')
activities = Attr(name='activities', multiple=True)
country = Attr(name='country')

estate_agent = Model(
    name='estate_agent',
    definition=True,
    dated=True,
    attrs=[
        name,
        website,
        contact_persons,
        address,
        postal_code,
        city,
        country,
        phone_number,
        carte_number,
        siret,
        rating,
        amount_renting,
        amount_selling,
        activities,
    ])
