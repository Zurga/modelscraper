from dispatcher import Dispatcher
from models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.efi_dumps
col = db.forum_post

efi_dumps = ScrapeModel(name='efi_dumps', domain='https://ghostlyhaks.com/',
    num_getters=2, runs=[

    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://ghostlyhaks.com/forum/rom-eeprom-bios-efi-uefi")],
        templates=(
            Template(
                name='forum_post', selector='.kbody tr',
                db_type='mongo_db', db='efi_dumps', table='forum_post',
                attrs=(
                    Attr(name='url', selector='a.ktopic-title', func='sel_url',
                        source=Source(active=False)), # source is for next run

                    Attr(name='user', selector='.kwho-user', func='sel_text'),

                    Attr(name='user_url', selector='.kwho-user', func='sel_url'),
                )
            ),
            Template(
                name='next_page', selector='.kpagination',
                attrs=[
                    Attr(name='url', selector='a', func='sel_url',
                        source=Source()) # source is for next run
                ]
            ),
        )
    ),

    Run(source_worker=WebSource, parser=HTMLParser,
        templates=(
            Template(
                name='forum_post', selector='a[href*=".zip"], a[href*=".tar"]',
                db_type='mongo_db', db='efi_dumps', table='efi_dumps',
                attrs=[Attr(name='url', selector='', func='sel_url')]
            ),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(efi_dumps)
disp.run()
