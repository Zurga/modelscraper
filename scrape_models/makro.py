from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


product_categories =  Phase(sources=(
        Source(url="https://www.makro.nl/cat/nl/products"),),
        templates=(
            Template(
                name='product_category',
                selector='#left-navigation-container ul.vertical > li > a',
                db_type='MongoDB', db='makro', table='product_categories',
                attrs=[
                    Attr(name='url', func='sel_url', source={'active': False}),
                ]
            ),
            )
    )

product_lists = Phase(templates=[
    Template(
        name='product_urls', selector='.product-list .product-tiles',
        db_type='MongoDB', db='makro', table='product_urls',
        attrs=[
            Attr(name='url', selector='.productname a', func='sel_url',
                    source={'active': False})
        ]
    ),
    Template(
        name='pagination', selector='.paging', attrs=[
            Attr(name='url', selector='a', func='sel_url', source=True),
        ]),
])

product = Phase(templates=[
    Template(
        name='product', db_type='MongoDB', db='makro', table='products',
        attrs=[
            Attr(name='name', selector='h1', func='sel_text'),
            Attr(name='price_gross', selector='.price-gross',
                    func='sel_text'),#  kws={'replacers': '€ '}),
            Attr(name='price_net', selector='.price-net',
                    func='sel_text'),# kws={'replacers': '€ '}),
            Attr(name='sku', selector='.articlenumber', func='sel_text'),
            Attr(name='description', selector='.tab-1', func='sel_text'),
            Attr(name='category', selector='li.normal', func='sel_text')
        ])
])

makro = ScrapeModel(
    name='makro', domain='https://www.makro.nl/', num_getters=1,
    phases=[product_categories, product_lists, product]
)
