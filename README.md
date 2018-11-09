# modelscraper
A webscraper which allows re-usage of components from other scrapers

By creating a model for the website you want to scrape, parts of the model can be used for other websites, or the model can be adapted for other websites.
The advantage of this is that scrapers don't have to be written specifically for each website and that the data from different sources which need to be grouped together have the same format.

Example that will scrape the search results from DuckDuckGo with the query "example":

<code>
from modelscraper.components import Template, Attr, Scraper
from modelscraper.sources import WebSource
from modelscraper.databases import CSV
from modelscraper.parsers import HTMLParser

db = CSV(db='duckduckgo', table='search_results')
htmlp = HTMLParser() 

results_source = WebSource(name='result', urls=['https://duckduckgo.com/html?q=example'])
next_pages_source = WebSource(name='next_page', session=results_source.session,
                              func='post', duplicate=True)

url = Attr(name='url', func=htmlp.url(selector='a'))
title = Attr(name='title', func=htmlp.text(selector='h2'))
snippet = Attr(name='snippet', func=htmlp.text(selector='.result__snippet'))

search_result = Template(
    name='search_result',
    source=[results_source, next_pages_source],
    database=db,
    selector=htmlp.select('.result'),
    attrs=[url, title, snippet])

input_fields = ['q', 's', 'nextParams', 'v', 'o', 'dc', 'api', 'kl']

next_page = Template(
    name='next_page',
    source=[results_source, next_pages_source],
    selector=htmlp.select('//input[@value="Next"]/..'),
    emits=next_pages_source,
    attrs=[
        Attr(name='url', value='https://duckduckgo.com/html'),
        *[Attr(name=field, func=htmlp.attr(selector='input[name="'+field+'"]',
                                            attr='value'))
          for field in input_fields]]
)

scraper = Scraper(templates=[search_result, next_page])
scraper.start()
</code>
To explain what is going on here I need to introduce some concepts
