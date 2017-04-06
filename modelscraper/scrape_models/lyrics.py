from parse_functions import *  # noqa
from lxml.cssselect import CSSSelector as css


clss = {
        'lyrics': {
            'skip_object': '',
            'start': [
                {'url': 'wiki/LyricWiki:Top_100',
                 'active': True,
                 },
            ],
            'list_url': 'http://lyrics.wikia.com/',
            'object_url': 'http://lyrics.wikia.com/',
            'css': {
                'list_class': css('li b a:not(a.new)'),
                'sections': {
                    'lyrics': {
                        'artist': {'func': parse_attr,
                                   'params': {
                                        'attr': 'content',
                                        'selector': css('meta[property=title]')
                                            }
                                   },
                        'lyric': {'func': parse_regex,
                                  'params': {
                                    'selector': css('.lyricbox'),
                                    'regex': ";([a-zA-z\d.,? '’\"!\(\)-]*)\n",
                                    }
                                  }
                    }
                }
            }
        }
}
