clss = {
    'peerwise': {
        'list_url': 'https://peerwise.cs.auckland.ac.nz/course/',
        'object_url': 'https://peerwise.cs.auckland.ac.nz/course/',
        'iter_suffix': '&offset=%d',
        'iter_stop': 50,
        'iter_modifier': 1,
        'iter_multiplier': 10,

        'start': [
            {'url': 'main.php?cmd=showAnsweredQuestions',
             'active': True,
             },
        ],
        'css': {
            'list_class': 'a.viewQ',
            'sections': {
                'question': {
                    '__or__correct_a': ['.displayHighlightOption',
                                        '.displayCircleAndHighlightOption',
                                        ],
                    'other_a': '.displayPlain',
                    'answers': '.displayAltText p',
                    'tags': '#tagsDisplay',
                    'comments': '.commentText',
                    'question_text': '#questionDisplay p',
                }
            },
        }
    }
}
