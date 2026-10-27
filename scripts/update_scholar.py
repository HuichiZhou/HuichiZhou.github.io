"""Fetch public Scholar counts without proxies; reject incomplete responses.

No data is written until every curated publication has been found. A blocked
request, CAPTCHA, changed markup, or partial response preserves the snapshot.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = '1IJyxpUAAAAJ'
PROFILE_URL = f'https://scholar.google.com/citations?user={PROFILE_ID}&hl=en'

class Element:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return ''.join(c.text() if isinstance(c, Element) else c for c in self.children).strip()
    def find(self, tag=None, cls=None, id=None):
        result = []
        for c in self.children:
            if isinstance(c, Element):
                if (tag is None or c.tag == tag) and (cls is None or cls in c.attrs.get('class','').split()) and (id is None or c.attrs.get('id') == id):
                    result.append(c)
                result.extend(c.find(tag,cls,id))
        return result

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.root, self.stack = Element(), []
        self.stack.append(self.root)
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(element)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break
    def handle_data(self, text):
        self.stack[-1].children.append(text)

def integer(text):
    value = re.sub(r'[,\s\u00a0]', '', text)
    if not re.fullmatch(r'\d+',value):
        raise ValueError('Unrecognized numeric value')
    return int(value)

def parse_page(html):
    dom = Document(html).root
    tables = dom.find(id='gsc_rsb_st')
    if len(tables) != 1:
        raise ValueError('Scholar statistics missing; the request may have been blocked')
    rows = tables[0].find(tag='tr')
    metrics = {}
    for index, key in enumerate(('citations','h_index','i10_index'),1):
        cells = rows[index].find(tag='td')
        metrics[key] = integer(cells[1].text())
    publications = {}
    for row in dom.find(tag='tr',cls='gsc_a_tr'):
        titles = row.find(tag='a',cls='gsc_a_at')
        if not titles:
            raise ValueError('A publication row has no title')
        a = titles[0]
        ref = parse_qs(urlparse(a.attrs['href']).query).get('citation_for_view',[''])[0]
        if not ref.startswith(PROFILE_ID+':'):
            raise ValueError('Unexpected Scholar profile in a publication link')
        sid = ref.split(':',1)[1]
        if not sid or sid in publications:
            raise ValueError('Empty or duplicate Scholar ID')
        citation_cells = row.find(tag='td',cls='gsc_a_c')
        if len(citation_cells) != 1:
            raise ValueError('Citation cell missing')
        citation_links = [a for a in citation_cells[0].find(tag='a') if a.text() != '*']
        text = citation_links[0].text() if citation_links else citation_cells[0].text()
        count = integer(text) if text else 0
        href = citation_links[0].attrs.get('href','') if citation_links and count else ''
        cited_url = urljoin(PROFILE_URL,href) if href else None
        if cited_url and urlparse(cited_url).hostname != 'scholar.google.com':
            raise ValueError('Unexpected citation destination')
        year = row.find(tag='td',cls='gsc_a_y')
        publications[sid] = {'title':a.text(), 'citations':count,
            'scholar_url':PROFILE_URL+'&view_op=view_citation&citation_for_view='+ref,
            'cited_by_url':cited_url, 'year':year[0].text() if year else ''}
    if not publications:
        raise ValueError('No publications returned')
    more = dom.find(id='gsc_bpf_more')
    if len(more) != 1:
        raise ValueError('Pagination state missing; cannot verify completeness')
    return metrics, publications, 'disabled' not in more[0].attrs

def fetch_html(url):
    request = Request(url, headers={'User-Agent':'HuichiZhou-website-citations/1.0 (+https://huichizhou.github.io/)', 'Accept-Language':'en'})
    with urlopen(request, timeout=25) as response:
        if urlparse(response.url).hostname != 'scholar.google.com':
            raise ValueError('Scholar redirected away from its public profile')
        return response.read(5_000_000).decode('utf-8')

def collect(fetch=fetch_html):
    publications, metrics = {}, None
    for _ in range(10):
        url = 'https://scholar.google.com/citations?'+urlencode({'user':PROFILE_ID,'hl':'en','cstart':len(publications),'pagesize':100})
        current_metrics, page, more = parse_page(fetch(url))
        if publications.keys() & page.keys():
            raise ValueError('Repeated page; refusing an incomplete snapshot')
        metrics = metrics or current_metrics
        publications.update(page)
        if not more:
            return {'profile_id':PROFILE_ID,'profile_url':PROFILE_URL,'source':'Google Scholar',
                    'updated_at':datetime.now(timezone.utc).isoformat(), 'metrics':metrics,'publications':publications}
    raise ValueError('Pagination limit exceeded')

def save_snapshot(snapshot, destination, required_ids):
    if not required_ids.issubset(snapshot['publications']):
        raise ValueError('Incomplete profile: one or more website publications are missing')
    # Preserve metadata captured during the original, verified browser import.
    old = json.loads(destination.read_text()) if destination.exists() else {'publications':{}}
    for sid, paper in snapshot['publications'].items():
        snapshot['publications'][sid] = {**old['publications'].get(sid,{}), **paper}
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(destination)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',type=Path,help='Parse a complete saved public profile instead of fetching it')
    args = parser.parse_args()
    try:
        groups = json.loads((ROOT/'data/publications.json').read_text())
        required = {p['scholar_id'] for g in groups for p in g['papers']}
        if args.html:
            metrics, publications, more = parse_page(args.html.read_text())
            if more:
                raise ValueError('Saved HTML does not contain all publications')
            snapshot = {'profile_id':PROFILE_ID,'profile_url':PROFILE_URL,'source':'Google Scholar','updated_at':datetime.now(timezone.utc).isoformat(),'metrics':metrics,'publications':publications}
        else:
            snapshot = collect()
        save_snapshot(snapshot,ROOT/'data/scholar.json',required)
        print(f'Updated citation data for {len(snapshot["publications"])} publications.')
    except Exception as exc:
        print(f'Scholar refresh unavailable; kept the last verified snapshot. {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
