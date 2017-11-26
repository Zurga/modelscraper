from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
import string


artists_url = 'http://www.metrolyrics.com/artists-{}.html'
artist_sources = (Source(url=artists_url.format(l)) for l in
                  ('1', *string.ascii_lowercase)) # noqa

artist_name = Attr(name='name', func='sel_text', selector='td:nth-of-type(1)')
genre = Attr(name='genre', func='sel_text', selector='td:nth-of-type(2)')
popularity = Attr(name='popularity', func='sel_attr', kws={'attr':'style'},
                  selector='td:nth-of-type(3) span span')
artist_url = Attr(name='url', func='sel_url',
                  selector='td:nth-of-type(1) a',
                  source={'active': False, 'parent': True})

artist_temp = Template(
    name='artist',
    selector='table.songs-table tbody tr',
    db_type='mongo_db',
    db='metrolyrics',
    table='artists',
    attrs=(artist_name, genre, popularity, artist_url))

pagination = Template(
    name='next_page',
    selector='.pagination',
    attrs=[Attr(name='number', func='sel_url', selector='a', source=True)]
)

song_year = Attr(name='year', func='sel_text', kws={'numbers':True},
                 selector='td:nth-of-type(3)')
song_url = Attr(name='song_url', func='sel_url',
                source={'active': False, 'copy_attrs': ['year', 'popularity']},
                selector='td:nth-of-type(2) a')

song_temp = Template(
    name='song',
    selector='table.songs-table tbody tr',
    db_type='mongo_db',
    db='metrolyrics',
    table='song_urls',
    attrs=(artist_name(selector='td:nth-of-type(2)'),
           popularity(selector='td:nth-of-type(4) span span'),
           song_year,
           song_url,
           )
)

lyric_attr = Attr(name='lyric', selector='#lyrics-body-text .verse',
                  func='sel_text')
writer_attr = Attr(name='writers', selector='.writers', func='sel_text')
album_attr = Attr(name='album', selector='a#album-name-link', func='sel_text')
lyric_name = Attr(name='name', selector='h1', func='sel_text')

lyrics_temp = Template(
    name='lyric',
    selector='.lyrics',
    db_type='mongo_db',
    db='metrolyrics',
    table='songs',
    attrs=(lyric_attr, writer_attr, album_attr, lyric_name)
)

lyrics = ScrapeModel(
    name='metrolyrics', domain='http://www.metrolyrics.ocm',
    phases=[
        Phase(n_workers=5, sources=artist_sources,
            templates=[artist_temp, pagination]),
        Phase(templates=[song_temp, pagination()]),
        Phase(templates=[lyrics_temp], synchronize=True)
    ])
disp = Dispatcher()
disp.add_scraper([lyrics])
disp.run()
