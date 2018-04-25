from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser


category_menu = Template(
    name='category_menu', selector='li.dropdown:nth-child(2)',
    attrs=[Attr(name='category', selector='a', source={'active': False},
                func='sel_url')])

name = Attr(name='name', selector='h1.box-title', func='sel_text')
street = Attr(name='street', selector='.street-address', func='sel_text')
postal = Attr(name='postal', selector='.postal-code', func='sel_text')
city = Attr(name='city', selector='.locality', func='sel_text')
telephone = Attr(name='telephone', selector='.tel', func='sel_text')
website = Attr(name='website', selector='.url a', func='sel_url')
mail = Attr(name='email', selector='.mail a', func='sel_url')
kvk = Attr(name='kvk', selector='.kvk a', func='sel_text')
description= Attr(name='description', selector='div[itemprop="description"] > p',
                  func='sel_text')
branches = Attr(name='branches', selector='.omschrijving a', func='sel_text')

company = Template(name='company', selector=None,
                   db_type='MongoDB', db='bedrijvenpagina',
                   table='companies', attrs=(name, street, postal, city,
                                             telephone, website, mail,
                                             kvk, description, branches))
result_list = Template(
    name='result', selector='.bedrijf',
    attrs=(Attr(name='url', selector='h3 a', func='sel_url',
                source={'active': False}),))
pagination = Template(
    name='pagination', selector='.pagers',
    attrs=(Attr(name='page', selector='a', func='sel_url',
                source=True),))

bedrijven_pagina = ScrapeModel(
    name='Bedrijven Pagina', domain='https://www.bedrijvenpagina.nl/',
    num_getters=2, phases=[
        Phase(source_worker=WebSource, parser=HTMLParser,
            sources=[Source(url='https://www.bedrijvenpagina.nl/')],
            templates=(category_menu,)),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(result_list, pagination)),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(company,))
    ]
    )


disp = Dispatcher()
disp.add_scraper(bedrijven_pagina)
disp.run()
