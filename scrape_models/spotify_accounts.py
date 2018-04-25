from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import TextParser


with open('/usr/share/wordlists/nmap.lst', encoding='utf8') as fle:
    words = set([''.join(c for c in w if c.isalpha()) for w in fle.readlines()])
base = 'https://www.spotify.com/nl/xhr/json/isEmailAvailable.php?email={}@mailinator.com'
sources = (Source(url=base.format(word),
                  attrs=(Attr(name='username', value=word),))
           for word in words)

result = Template(
    name='username',
    db='spotify',
    table='users',
    db_type='MongoDB',
    attrs=[
        Attr(
            name='exists',
            func='sel_text'
        )
    ]
)

user = ScrapeModel(
    name='spotify',
    phases=[
        Phase(sources=sources, n_workers=10,
              templates=[result]
              )
    ]
)


