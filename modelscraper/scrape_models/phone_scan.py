import dispatcher
import models
from functions.store_functions import *
from functions.parse_functions import *
import pandas as pd


with open('pros.json') as pros:
    results = json.load(pros)
    results = [{**res['advert'], **res['personal'], 'url': res['url']} for res in results if 'onbe' not in res['advert']['prices']]
    results = [res for res in results if type(res['prices']) != list]

    df = pd.DataFrame(res for res in results)

    df['prices'] = df['prices'].apply(lambda x: float(x.replace('€ ', '')))
    df['age'] = df['age'].apply(lambda x: int(x))
    df['poss_len'] = df['possibilities'].apply(lambda x: len(x))
    companies = list(key for key,val in df.phone.value_counts().items() if val > 1)

    df = df[df.phone.isin(companies) == False]

    df = df[ df.prices < 300]
    df = df[ df.prices > 40]
data = 'lsd=AVqcfDvD&charset_test=%E2%82%AC%2C%C2%B4%2C%E2%82%AC%2C%C2%B4%2C%E6%B0%B4%2C%D0%94%2C%D0%84&version=1&ajax=0&width=0&pxr=0&gps=0&dimensions=0&m_ts=1461427436&li=7JwbV4q78ADNzenw4vlokKwh&email=jim.lemmers%40gmail.com&pass=thisclassicpursetoldfacebook&login=Aanmelden'
model = models.ScrapeModel(name='pros', domain='https://m.facebook.com', num_getters=1, runs=[
    models.Run(getters=[models.Getter(url='https://m.facebook.com/login.php?refsrc=https%3A%2F%2Fm.facebook.com%2Fhome.php&lwv=100&refid=8',
                                      data=data, method='post', parse=False)]),
    models.Run(getters=(models.Getter(url='https://m.facebook.com/search/people/?q={}'.format(i)) for i
                        in df.phone),
            templates=[
                models.Template(
                    name='person', selector='.bl',
                    attrs=[
                        models.Attr(name='website', selector='a', func=sel_attr,
                                    kws={'attr': 'href'}),
                    ], store=models.StoreObject(func=store_mongo, kws={'db': 'prossies', 'collection': 'fb'})
                ),
            ]
            )
        ],
    )

disp = dispatcher.Dispatcher()
disp.add_scraper(model)
disp.run()
