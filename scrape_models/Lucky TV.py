from modelscraper import Scraper, Model, Attr, WebSource, HTMLParser, Sqlite


sources = WebSource(urls=("http://www.luckytv.nl/afleveringen/page/{}/".format(i)
           for i in range(1, 50)))
db = Sqlite(db='luckytv')
html = HTMLParser()

episode = Model(
    source=sources,
    name='episode', selector=html.select('article.video'),
    database=db, table='episodes',
    attrs=(
        Attr(name='url', func=html.url(selector='a:nth-of-type(1)')),
        Attr(name='title', func=html.text(selector='.video__title')),
        Attr(name='date', func=html.text(selector='.video__date')),
    )
)

LuckyTV = Scraper(
    name='Lucky TV',
    models=[episode])
