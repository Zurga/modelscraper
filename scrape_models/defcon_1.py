from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.sources import ProgramSource, WebSource
from modelscraper.parsers import TextParser, CSVParser
from .objects.networking import ip_phase, ip_template, port_phase

from pymongo import MongoClient


no_ip = MongoClient().defcon.companies.find({'website': {'$ne': None},
                                             'ip': {'$exists': False}})
companies2 = MongoClient().defcon.companies.find({'website': {'$ne': None}})

defcon_base = Template(
    db='defcon',
    db_type='MongoDB'
)

jacco_base = 'jackling.nl'
jacco = (Source(url='jackling.nl'),)
jacco_git = (Source(url='http://{}/.git/config'.format(jacco_base)),)
jacco_ds = (Source(url='http://{}/.DS_STORE'.format(jacco_base)),)

git_sources = (Source(url='http://{}/.git/config'.format(c['website']), attrs=[
    Attr(name='kvk', value=c['id'])], copy_attrs='kvk') for c in companies2)
ds_store_sources = (Source(url='http://{}/.DS_STORE'.format(c['website']), attrs=[
    Attr(name='kvk', value=c['id'])], copy_attrs='kvk') for c in companies2)

git_template = Template(
    name='Git exposed', db_type='MongoDB', db='defcon',
    table='git', attrs=(
        Attr(name='vulnerable', func='sel_text', kws={'needle': '[core]'}),
    )
)

ds_store_template = Template(
    name='DS_STORE exposed', db_type='MongoDB', db='defcon',
    table='ds_store', attrs=(
        Attr(name='vulnerable', func='sel_text'),
    )
)

robot_template = defcon_base(
    name='RSA exploit', db_type='MongoDB', db='defcon',
    table='robot', attrs=(
        Attr(name='vulnerable', func='sel_text', selector=0),
        Attr(name='ip', func='sel_text', selector=2),
    )
)

wordpress_template = defcon_base(
    name='Wordpress exploits', table='wordpress',
    parser=TextParser,
    attrs=[
    ]
)

wordpress_source = ProgramSource(
    function='yes y | wpscan {} --batch --follow-redirection'
)

robot_source = ProgramSource(
    function='/home/jim/git/robot-detect/robot-detect --csv -q {}')

passwords_source = ProgramSource(
    function='grep -ra @{}: ~/ideas/BreachCompilation/data'
)

defcon_1 = ScrapeModel(name='nmap_test', domain='', num_getters=1, phases=[
    ip_phase(
        n_workers=10,
        templates=[
            ip_template(
                db='defcon',
                table='companies',
                func='update',
                kws={'key': '_id'},
                source=['ip'])
        ],
        sources=jacco
    ),
    port_phase,
    Phase(templates=[git_template], sources=jacco_git, parser=TextParser),
    Phase(templates=[ds_store_template], sources=jacco_ds, parser=TextParser)

])
