import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_scholar import PROFILE_ID, collect, parse_page, save_snapshot
from build import ROOT, render

def page(ids=('one','zero'), more=False, count='1,642'):
    rows = ''.join(f'''<tr class="gsc_a_tr"><td><a class="gsc_a_at" href="/citations?citation_for_view={PROFILE_ID}:{sid}">Paper &amp; {sid}</a></td><td class="gsc_a_c"><a href="/scholar?cites=123">{'12' if sid != 'zero' else ''}</a><a>*</a></td><td class="gsc_a_y"><span>2026</span></td></tr>''' for sid in ids)
    return f'''<table id="gsc_rsb_st"><tr><th></th><th>All</th></tr><tr><td>Citations</td><td>{count}</td></tr><tr><td>h-index</td><td>15</td></tr><tr><td>i10-index</td><td>20</td></tr></table><table>{rows}</table><button id="gsc_bpf_more" {'' if more else 'disabled'}>Show more</button>'''

class ScholarTests(unittest.TestCase):
    def test_counts_links_and_zero_citation(self):
        metrics,papers,more=parse_page(page())
        self.assertEqual(metrics['citations'],1642)
        self.assertEqual(papers['one']['citations'],12)
        self.assertEqual(papers['zero']['citations'],0)
        self.assertIsNone(papers['zero']['cited_by_url'])
        self.assertEqual(papers['one']['title'],'Paper & one')
        self.assertEqual(papers['one']['cited_by_url'],'https://scholar.google.com/scholar?cites=123')
        self.assertFalse(more)

    def test_captcha_malformed_counts_wrong_profile_rejected(self):
        for html in ('<html>Sorry, unusual traffic. CAPTCHA</html>',page(count='unknown'),page().replace(PROFILE_ID,'different-user')):
            with self.subTest(html=html[:40]), self.assertRaises((ValueError,IndexError)):
                parse_page(html)

    def test_pagination_and_repeated_page(self):
        pages=iter([page(('first',),True),page(('second',))])
        result=collect(lambda url:next(pages))
        self.assertEqual(set(result['publications']),{'first','second'})
        with self.assertRaises(ValueError):
            collect(lambda url:page(('first',),True))

    def test_incomplete_refresh_preserves_file_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'scholar.json'
            original=b'{"publications":{"important":{"citations":80}},"updated_at":"2026-10-27"}\n'
            path.write_bytes(original)
            with self.assertRaises(ValueError):
                save_snapshot({'publications':{'other':{'citations':1}}},path,{'important'})
            self.assertEqual(path.read_bytes(),original)

    def test_every_curated_paper_has_correct_static_citation(self):
        groups=json.loads((ROOT/'data/publications.json').read_text())
        scholar=json.loads((ROOT/'data/scholar.json').read_text())
        html=render(groups,scholar)
        ids=[p['scholar_id'] for g in groups for p in g['papers']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(set(ids).issubset(scholar['publications']))
        self.assertEqual(html.count('class="citation-link"'),len(ids))
        self.assertNotIn('href="#"',html)
        self.assertNotIn('{{',html)
        self.assertNotIn('allorigins',html)
        for sid in ids:
            self.assertIn(f'id="paper-{sid}"',html)
        bad=copy.deepcopy(scholar)
        bad['publications'][ids[0]]['citations']=-1
        with self.assertRaises(ValueError):
            render(groups,bad)

if __name__ == '__main__':
    unittest.main()
