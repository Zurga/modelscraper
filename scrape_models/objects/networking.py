from modelscraper.components import Phase, Template, Attr
from modelscraper.sources import BaseSourceWorker, ProgramSource
from modelscraper.parsers import TextParser
import dns.resolver
import dns.query
import dns.zone


ip_template = Template(
    name='ip',
    db_type='MongoDB', db='',
    table='',
    parser=TextParser, attrs=(
        Attr(
            name='ip', func='sel_text',
            kws={'regex': '(\d+\.\d+\.\d+\.\d+)'},
        ),
    )
)

ip_phase = Phase(
    n_workers=10,
    templates=[ip_template],
    source_worker=ProgramSource(function='host {}')
)

port_template = Template(
    name='ports', selector='port', db_type='MongoDB', db='monog',
    table='ports', attrs=(
    Attr(name='portnumber', func='sel_attr',
         kws={'attr': 'portid'}),
    Attr(name='state', selector='state', func='sel_attr',
         kws={'attr': 'state'}),
    Attr(name='service', selector='service', func='sel_attr',
         kws={'attr': 'name'}))
)

port_phase = Phase(
    n_workers=5,
    source_worker=ProgramSource(
        function='sudo masscan -oX - -p0-10000 --rate 1000 --range {}'),
    templates=[port_template])

class AXFRSource(BaseSourceWorker):
    """
    A class that can retrieve the subdomains from an AXFR query.
    Returns a string with newlines seperating the subdomains.
    """
    def retrieve(self, source):
        domain = source.url.strip()
        found = set()
        try:
            ns_query = dns.resolver.query(domain,'NS')
            for ns in ns_query.rrset:
                nameserver = str(ns)[:-1]
                if nameserver is None or nameserver == "":
                    continue
                try:
                    axfr = dns.query.xfr(nameserver, domain, lifetime=5)
                    try:
                        zone = dns.zone.from_xfr(axfr)
                        if zone is None:
                                continue
                        for name, node in zone.nodes.items():
                            rdatasets = node.rdatasets
                            for rdataset in rdatasets:
                                found.add((name, str(rdataset)))
                    except Exception as e:
                        continue
                except Exception as e:
                    continue
        except Exception as e:
            pass
        return '\n'.join(found)
