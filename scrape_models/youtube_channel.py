from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers.html_parser import HTMLParser


cl = MongoClient()
db = cl.youtube_channel
col = db.channel_videos

# The base url of the website
url = 'https://youtube.com/'

# The amount of workers that will get the information

youtube_channel = ScrapeModel(
    name='youtube_channel', domain='https://youtube.com/', num_getters=2, awaiting=True,
    phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url='https://www.youtube.com/user/ozzymanreviews/videos'),
        Source(url='https://www.youtube.com/user/Draadstal/videos'),
        Source(url='https://www.youtube.com/channel/UCQMs9pijXYAdqvkEMJyCM4g/videos'),
        Source(url='https://www.youtube.com/channel/UCi1LpRIlG1tDY5Z54VTel2w/videos'),
        Source(url='https://www.youtube.com/user/vpro/videos'),
        Source(url='https://www.youtube.com/user/nprmusic/videos'),
    ],
        templates=(
            Template(
                name='channel_videos', selector='li.channels-content-item',
                db_type='MongoDB', db='youtube_channel', table='channel_videos',
                attrs=[
                    Attr(name='url', selector='h3.yt-lockup-title a', func='sel_url'),

                    Attr(name='title', selector='h3', func='sel_text'),

                    Attr(name='views', selector='.yt-lockup-meta-info', func='sel_text',
                         kws={'regex': '(.*) weergaven', 'numbers': True}),
                ]
            ),
            Template(
                name='next_videos', selector='.browse-items-load-more-button',
                attrs=[
                    Attr(name='url', func='sel_attr',
                         kws={'attr': 'data-uix-load-more-href'},
                         source=Source(src_template='http://youtube.com{}',
                                       json_key=['content_html', 'load_more_widget_html']))
                ]),
        )
    ),
    ]
)


disp = Dispatcher()
disp.add_scraper(youtube_channel)
disp.run()
