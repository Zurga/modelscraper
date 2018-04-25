from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


filepath = '/mnt/Movies/theoffice/'
create_dir = 'sudo mkdir -p '+ filepath +'/{season}/'
youtube_dl = 'sudo youtube-dl -o ' + filepath + '{season}/{episode} {url}'
extended_url = 'http://watchtheoffice.online/the-office-s{02d}e{02d}-extended/'

theoffice = ScrapeModel(name='theoffice', domain='http://watchtheofficeonline.com',
    num_getters=2, phases=[
    Phase(
        sources=[Source(url=extended_url.format(season, episode))
                 for season in range(1, 10) for episode in range(1, 30)],
        templates=(
            Template(
                name='episode', selector='#Rapidvideo',
                db_type='ShellCommand', db='theoffice', table='season',
                kws={'command': create_dir + ' & ' + youtube_dl},
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
