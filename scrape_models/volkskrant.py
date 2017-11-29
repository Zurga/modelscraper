from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
import datetime
from parsers import HTMLParser


cl = MongoClient()
db = cl.volkskrant
col = db.artikelen

today = datetime.datetime.now().year
print(today)

volkskrant = ScrapeModel(
    name='volkskrant', domain='http://www.volkskrant.nl/', num_getters=2,
    cookies={'nl_cookiewall_version': '1'}, phases=[
        Phase(source_worker=WebSource, parser=HTMLParser, sources=[
            Source(url="http://www.volkskrant.nl/archief/{}".format(year))
            for year in range(1987, today)],
            templates=(
                Template(
                    name='day_url', selector='td', attrs=(
                        Attr(name='url', selector='a', func='sel_url',
                             source=Source(active=False)),
                        )
                    ),
                )
            ),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(
                Template(
                    name='article_url', selector='article',
                    attrs=(
                        Attr(name='url', selector='a', func='sel_url',
                             source=Source(active=False)),
                        )
                    ),
                Template(
                    name='next_page_url', selector='a.pager',
                    attrs=(
                        Attr(name='url', selector='', func='sel_url',
                             source=True),
                        )
                    ),
                ),
            ),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(
                Template(
                    name='article', selector='',
                    db_type='mongo_db', db='volkskrant', table='articles',
                    attrs=(
                        Attr(name='url', selector='a', func='sel_url',
                             source=Source(active=False)),
                        Attr(name='title', selector='h1', func='sel_text'),
                        Attr(name='subtitle', selector='h2', func='sel_text'),
                        Attr(name='author', selector='span[itemprop="author"]',
                             func='sel_text'),
                        Attr(name='author',
                             selector='time[itemprop="datePublished"]',
                             func='sel_text'),
                        Attr(name='category',
                             selector='meta[property="article:section"]',
                             func='sel_attr', kws={'attr': 'content'}),
                        Attr(name='description',
                             selector='p[itemprop="description"]',
                             func='sel_text'),
                        Attr(name='text', selector='.article__body__paragraph',
                             func='sel_text'),
                        )
                    ),
                )
            ),
])

disp = Dispatcher()
disp.add_scraper(volkskrant)
disp.run()
