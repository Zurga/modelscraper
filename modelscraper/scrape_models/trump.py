from models import *  #noqa
from dispatcher import Dispatcher
import random


form_fields = {'name1': 'Don',
                'name2': 'Rump',
                'email1': 'donrump%d@mailinator.com' %(random.randint(0, 1000)),
                'state[]': "Nebraska",
                'zip': '92466',
                'availability[]': 'part+20',
                'Contact[]': "anytime",
                'Skills+and+Interests[]': 'Research',
                'help1[]': 'Online',
                'issues1[]': 'Jobs',
                'Referred+[]': 'friend',
                'action': 'dhvc_form_ajax',
                '_dhvc_form_is_ajax_call': '1',
                'form_url': "http://citizensfortrump.com/get-involved/",
                }

vote = ScrapeModel(name='trumpvolunteer', domain='citizensfortrump.com', runs=[
    Run(to_getter=[
        Getter(url='http://citizensfortrump.com/get-involved',
            meta_attrs=[Attr(name=key, value=val) for key, val in form_fields.items()])
        ],
        objects=[
            HTMLObject(selector='.dhvcform-276', attrs=[
                Attr(name='_dhvc_form_nonce', selector='input[name="_dhvc_form_nonce"]',
                     parse_func='sel_attr', kwargs={'attr': 'value'}),
                Attr(name='dhvc_form', selector='input[name="dhvc_form"]', parse_func='sel_attr',
                     kwargs={'attr': 'value'}),
                Attr(name='post_id', selector='input[name="post_id"]', parse_func='sel_attr',
                     kwargs={'attr': 'value'}),
                Attr(name='post_id', selector='input[name="post_id"]', parse_func='sel_attr',
                     kwargs={'attr': 'value'}),
                Attr(name='post_id', selector='input[name="post_id"]', parse_func='sel_attr',
                     kwargs={'attr': 'value'}),
            ], getter=Getter(url='http://citizensfortrump.com/wp-admin/admin-ajax.php',
                             request='post', parse=False))
        ], repeat=True)
])

disp = Dispatcher()
disp.add_scraper(vote)
disp.run()
