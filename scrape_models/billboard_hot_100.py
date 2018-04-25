from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from datetime import datetime
from pymongo import MongoClient


cl = MongoClient().billboard.songs
years = set([a['url'] for a in cl.find()])
print(years)
cl = MongoClient().billboard2.songs
cl.drop()
#start = (Source(url='https://www.billboard.com/charts/hot-100/1958-08-04',
#                attrs=[Attr(name='year', value='1958-08-04')]),)
start = (Source(url=y, attrs=[Attr(name='year', value=y.split('/')[-1])])
         for y in years)

name = Attr(
    name='song_name',
    selector='.chart-row__song',
    func='sel_text')

artist = Attr(
    name='artist',
    selector='.chart-row__artist',
    func='sel_text')

position = Attr(
    name='position',
    selector='.chart-row__current-week',
    func='sel_text',
    kws={'numbers':True})

song = Template(
    name='song',
    selector='.chart-row__main-display',
    db_type='MongoDB',
    db='billboard',
    table='songs2',
    required=True,
    attrs=[
        name,
        artist,
        position
    ])

next_date = Template(
    name='next_date',
    selector='#chart-nav',
    required=True,
    attrs=[
        Attr(name='next_week', func='sel_url',
             selector='a[title="Next Week"]',
             source={'copy_attrs': 'year'}),
        Attr(name='year',
             func='sel_url',
             selector='a[title="Next Week"]',
             kws={'regex': '\/([0-9\-]+)'}
             )
    ]
)

charts = ScrapeModel(
    name='Hot 100',
    domain='https://www.billboard.com/',
    phases=[
        Phase(n_workers=5, sources=start,
              templates=[song, next_date])
    ])
