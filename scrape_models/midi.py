from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser

title = Attr(name='title', func='sel_text')
artist = Attr(name='artist', func='sel_text')
midi_url = Attr(name='midi_url')

song = Template(
    name='song', db_type='MongoDB', db='midi', table='songs',
    attrs=[
        title,
        artist,
        midi_url
    ])

freemidi_template = song(
    table='freemidi', selector='#mainContent div.col-xs-12:nth-of-type(1)',
    attrs=[
        title(selector='li.active:nth-child(3) > a:nth-child(1) > span:nth-child(1)'),
        artist(selector='ol.breadcrumb:nth-child(1) > li:nth-child(2) > a:nth-child(1) > span:nth-child(1)'),
    ])

freemidi_sources = (
    Source(url='https://freemidi.org/download-{}'.format(i),
           attrs=[midi_url(value='https://freemidi.org/getter-{}'.format(i))])
    for i in range(25803))

freemidi = ScrapeModel(
    domain='http://freemidi.org',
    phases=[
        Phase(n_workers=3, sources=freemidi_sources, templates=[freemidi_template])
    ])
