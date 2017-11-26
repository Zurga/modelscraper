from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


uefa = ScrapeModel(
    name='eufa', domain='http://uefa.com', num_getters=2, phases=[
    Phase(sources=(
        Source(url="http://www.uefa.com/uefaeuro/season=2016/teams/index.html"),),
        templates=(
            Template(
                name='team', selector='.teams--qualified',
                attrs=[
                    Attr(name='url', selector='a',
                                func='sel_url', source={'active': False}),
                ]
            ),)
    ),
    Phase(synchronize=False,templates=[
            Template(
                name='player', selector='.squad--team-player',
                db_type='mongo_db', db='uefa', table='players',
                attrs=[
                    Attr(name='name', selector='.squad--player-name',
                                func='sel_text'),
                    Attr(name='player_url', selector='.squad--player-name a',
                                func='sel_url'),
                    Attr(name='img', selector='.squad--player-img img',
                                func='sel_attr', kws={'attr': 'src'}),
                ]
            ),
            # Template(
            #     name='team', selector='',
            #     db_type='mongo_db', func='update', db='uefa', table='players',
            #     attrs=[
            #         Attr(name='team', selector='h1.team-name', func='sel_text'),
            #     ]
            # )
        ]
    )]
)

disp = Dispatcher()
disp.add_scraper(uefa)
disp.run()
