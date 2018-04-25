from raper.dispatcher import Dispatcher
from raper import models

data = 'sid={}&options%5B%5D=display_full_history&options%5B%5D=use_cached_data_only&action=View+Complete+Tracking+History'
#data =

metro = ScrapeModel(name='landmark', domain='https://mercury.landmarkglobal.com/', num_get=2, phases=[
    Phase(sources=(
        Source(url="https://mercury.landmarkglobal.com/tracking/track.php?trck=LTN{}N1&Submit=Track".format(i),
                      method='post', data=[('sid', str(i)),('options[]', 'display_full_history'),
                                           ('options[]','use_cached_data_only'),
                                           ('action','View+Complete+Tracking+History')])
                for i in range(5000, 50000000)),
        templates=[
            Template(
                name='shipment', selector=None, db='shipments', db_type='MongoDB',
                table='shipment', attrs=[
                    Attr(name='carrier', selector='#large_shipment_info_box > div:nth-child(2) > div:nth-child(1)',
                                func='sel_text', kws={'regex': 'Carrier:\s(\w+)'}),
                    Attr(name='shipped_to', selector='#large_shipment_info_box > div:nth-child(2) > div:nth-child(2) div:nth-child(1) .align_left',
                                func='sel_text'),
                    Attr(name='shipped_from', selector='#large_shipment_info_box > div:nth-child(2) > div:nth-child(2) div:nth-child(2) .align_left',
                                func='sel_text'),
                ]),
            Template(
                name='event', selector='table tr:not(:nth-child(1))', db_type='MongoDB', db='shipments', table='events', attrs=[
                    Attr(name='description', selector='td:nth-of-type(1)', func='sel_text'),
                    Attr(name='date', selector='td:nth-of-type(2)', func='sel_text'),
                    Attr(name='location', selector='td:nth-of-type(3)', func='sel_text'),
                ]),
        ]
    )
])

d = Dispatcher()
d.add_scraper(metro)
d.run()
