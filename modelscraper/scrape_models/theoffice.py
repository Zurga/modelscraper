from dispatcher import Dispatcher
from models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.theoffice
col = db.season

filepath = '/mnt/Movies/theoffice/'

theoffice = ScrapeModel(name='theoffice', domain='http://watchtheofficeonline.com',
    num_getters=2, runs=[
    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://watchtheofficeonline.com/s{}e{}".format(season,
                                                                   episode))
        for season in range(1, 10) for episode in range(1, 30)],
        templates=(
            Template(
                name='episode', selector='.so-panel.widget.widget_siteorigin-panels-builder',
                db_type='shell_command', db='theoffice', table='season',
                kws={'command': 'sudo mkdir -p '+ filepath +'/{season}/ &' +
                     ' sudo youtube-dl -o /mnt/Movies/{season}/{episode} {url}'},
                attrs=(
                    Attr(name='url', selector='a', func=['sel_url', 'sel_text'],
                         kws=[{}, {'needle': r'.*(s\d+e\d+)'}]),
                    Attr(name='episode', selector='.textwidget', func='sel_text',
                         kws={'index': 3, 'substitute': '_', 'replacers': ' '}),
                    Attr(name='season', selector='.textwidget',
                         func='sel_text', kws={'index': 1, 'replacers': ' '}),
                )
            ),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(theoffice)
disp.run()
