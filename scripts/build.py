"""Render a complete, JavaScript-optional homepage from curated data."""
import json
import hashlib
import re
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def render_template(name, values):
    values = {**values, 'STYLE_VERSION': hashlib.sha256((ROOT/'stylesheet.css').read_bytes()).hexdigest()[:12]}
    return re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], (ROOT/'templates'/name).read_text())

def render(groups, scholar):
    sections, seen = [], set()
    for number, group in enumerate(groups, 1):
        cards = []
        for paper in group['papers']:
            sid = paper['scholar_id']
            if sid in seen:
                raise ValueError('Duplicate Scholar ID: ' + sid)
            seen.add(sid)
            citation = scholar['publications'][sid]
            count = citation['citations']
            if type(count) is not int or count < 0:
                raise ValueError('Invalid citation count: ' + sid)
            authors = escape(paper['authors']).replace('Huichi Zhou', '<strong>Huichi Zhou</strong>')
            authors_html = f'<p class="paper-authors">{authors}</p>'
            author_names = paper['authors'].split(', ')
            if len(author_names) > 14:
                short = author_names[:3]
                own = next((a for a in author_names if 'Huichi Zhou' in a),None)
                if own and own not in short:
                    short += ['…',own]
                short_text = escape(', '.join(short)+', …').replace('Huichi Zhou','<strong>Huichi Zhou</strong>')
                authors_html = f'<details class="author-details"><summary><span>{short_text}</span><span class="all-authors">All {len(author_names)} authors</span></summary><p class="paper-authors">{authors}</p></details>'
            links = []
            for link in paper['links']:
                if not link['url'].startswith('https://'):
                    raise ValueError('Expected an HTTPS publication link')
                label = escape(link['label'])
                if link['label'] == 'Code' and paper.get('github_repo'):
                    label += f' <span class="github-stars" data-repo="{escape(paper["github_repo"])}"></span>'
                links.append(f'<a href="{escape(link["url"])}" target="_blank" rel="noopener noreferrer">{label} <span aria-hidden="true">↗</span></a>')
            links.append(f'<a href="{escape(citation["scholar_url"])}" target="_blank" rel="noopener noreferrer">Scholar <span aria-hidden="true">↗</span></a>')
            cited_url = citation.get('cited_by_url') or citation['scholar_url']
            noun = 'citation' if count == 1 else 'citations'
            label = f'{count:,} {noun}'
            citation_link = f'<a class="citation-link" href="{escape(cited_url)}" target="_blank" rel="noopener noreferrer" aria-label="{escape(label + " on Google Scholar for " + paper["title"])}">Cited by <strong>{count:,}</strong> <span aria-hidden="true">↗</span></a>'
            search = ' '.join(str(paper[k]) for k in ('title','authors','venue','year'))
            cards.append(f'''<article class="paper" id="paper-{sid}" data-search="{escape(search)}">
              <div class="paper-meta"><span class="paper-type">{escape(paper['type'])}</span><span>{paper['year']}</span></div>
              <h3>{escape(paper['title'])}</h3>{authors_html}<p class="paper-venue">{escape(paper['venue'])}</p><div class="paper-links">{citation_link}{''.join(links)}</div>
            </article>''')
        sections.append(f'''<details class="publication-group" data-topic="{escape(group['id'])}" open><summary><span class="group-number">{number:02}</span><h3>{escape(group['title'])}</h3><span class="group-count">{len(cards)} papers</span><span class="disclosure" aria-hidden="true">−</span></summary><div class="group-papers">{''.join(cards)}</div></details>''')
    updated = datetime.fromisoformat(scholar['updated_at'].replace('Z','+00:00'))
    values = {'PUBLICATIONS':'\n'.join(sections), 'PAPER_COUNT':str(len(seen)), 'PROFILE_URL':escape(scholar['profile_url']), 'CITATIONS':format(scholar['metrics']['citations'],','), 'H_INDEX':str(scholar['metrics']['h_index']), 'UPDATED_ISO':updated.date().isoformat(), 'UPDATED_DATE':f'{updated.day} {updated:%b %Y}', 'TOPIC_OPTIONS':''.join(f'<option value="{escape(g["id"])}">{escape(g["title"])}</option>' for g in groups)}
    return render_template('index.html', values)

def main():
    groups = json.loads((ROOT/'data/publications.json').read_text())
    scholar = json.loads((ROOT/'data/scholar.json').read_text())
    (ROOT/'index.html').write_text(render(groups,scholar))
    (ROOT/'logs').mkdir(exist_ok=True)
    (ROOT/'logs/index.html').write_text(render_template('logs.html', {}))
    print(f'Rendered {sum(len(g["papers"]) for g in groups)} publications and the Logs page.')

if __name__ == '__main__':
    main()
