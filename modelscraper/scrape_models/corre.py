from lxml.cssselect import CSSSelector as css
from dispatcher import Dispatcher
from models import *  # noqa
from workers import WebSource
from parsers import HTMLParser
# een run kan gezien worden als een keer dat de scraper de website bezoekt
# de keys die in de "css" key zitten worden door de parser 1 op 1 in een
# dictionary gezet die dan wordt opgeslagen. Door een forward key aan te
# geven kan de url in de volgende run gebruikt worden om te scrapen. Dit
# maakt het mogelijk om bijvoorbeeld de urls uit een menu van de website
# op te halen en die dan weer allemaal weer in een volgende run te
# gebruiken.
# De 'pre_parser' key geeft selecteerd html elementen waarover geitereerd
# en respectievelijk de functies worden toegepast om de informatie uit de
# elementen te halen.
# Elk dictionary in de 'to_parser' lijst geeft zijn eigen dictionary terug in
# de resultaten. Dit zorgt nog wel voor wat inconsistentie in de output, maar
# dat ga ik nog proberen aan te pakken.

login_source = Source(
    url='https://decorrespondent.nl/login', method='post',
    params={'email': 'jim.lemmers@gmail.com',
            'password': 'thisclassicpursetoldcorrespondent'})

article_sources = [
    Source(url='http://decorrespondent.nl/api2/collection/home/{}'.format(i),
           json_key=['meta', 'html'])
    for i in range(1, 3)]

article_sources.prepend(Source(url='http://decorrespondent.nl/'))

comment_template = Template(
    name='comment', selector='.comment-inner-container', db='correspondent',
    table='comments2', attrs=[
        Attr(name='text', func='sel_text', selector='.comment-text'),
        Attr(name='id', func='sel_attr', kws={'attr': 'data-id'},
             selector='.comment-action-menu-container'),
        Attr(name='name', func='sel_text', selector='.user-name'),
    ])

article_template = Template(
    name='article', db_type='mongo_db', db='correspondent',
    table='articles2', preview=True,
    attrs=[
        Attr(name='title', func='sel_text', selector='.article-head-title'),

        Attr(name='article_id', func='sel_attr',
             selector='section.publication',
             kws={'attr': 'data-publication-id'},
             source=Source(
                 active=False,
                 src_template='http://decorrespondent.nl/api2/publication/{}/comments',
                 json_key=['meta', 'comments_rendered'])),

        Attr(name='text', func='sel_text',
             selector='.article-body-text > p'),

        Attr(name='author', func='sel_text',
             selector='.publication-authors-names-name.author-name'),

        Attr(name='author_url', func='sel_url',
             selector='.publication-authors-names-name.author-name'),

        Attr(name='author_department', func='sel_text',
             selector='.publication-authors-department'),

        Attr(name='reading_time', func='sel_text',
             selector='.mod-readingtime'),

        Attr(name='published', func='sel_attr',
             selector='time.article-metadata-data',
             kws={'attr': 'datetime'}),

        Attr(name='intro', func='sel_text',
             selector='.article-head-lead-text'),

        Attr(name='article_type', func='sel_text',
             selector='.publication-labels'),

        Attr(name='recommending_author', func='sel_text',
             selector='.recommendation-author-name'),

        Attr(name='recommending_author_url', func='sel_url',
             selector='.recommendation-author-name'),

        Attr(name='recommending_author_description', func='sel_text',
             selector='.recommendation-author-description'),
    ])

article_link_template = Template(
    name='link', selector='.feed-items-item',
    attrs=[
        Attr(name='link', func='sel_url',
             selector='a.article-preview-default-top',
             source={'active': False}),
    ])

correspondent = ScrapeModel(
    name='correspondent', domain='https://decorrespondent.nl',
    runs=[
        Run(source_worker=WebSource, parser=HTMLParser, sources=[login_source]),

        Run(source_worker=WebSource, parser=HTMLParser, sources=article_sources,
            templates=[article_link_template]),

        Run(source_worker=WebSource, parser=HTMLParser,
            templates=[article_template]),

        Run(source_worker=WebSource, parser=HTMLParser,
            templates=[comment_template]),
    ]
)

disp = Dispatcher()
disp.add_scraper(correspondent)
disp.run()
