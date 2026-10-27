"""Render a complete, JavaScript-optional homepage from curated data."""
import json
import hashlib
import re
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def render_news(entries):
    rows = []
    for entry in sorted(entries, key=lambda item: item['date'], reverse=True):
        date = entry['date']
        if re.fullmatch(r'\d{4}-\d{2}', date):
            parsed = datetime.strptime(date, '%Y-%m')
            date_label = f'{parsed:%b %Y}'
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            parsed = datetime.strptime(date, '%Y-%m-%d')
            date_label = f'{parsed.day} {parsed:%b %Y}'
        else:
            raise ValueError('Expected a news date in YYYY-MM or YYYY-MM-DD format')
        links = []
        for link in entry.get('links', []):
            url = link['url']
            if not (url.startswith('https://') or (url.startswith('#') and len(url) > 1)):
                raise ValueError('Expected an HTTPS URL or section anchor for a news link')
            external = ' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else ''
            arrow = '↗' if external else '→'
            links.append(f'<a href="{escape(url)}"{external}>{escape(link["label"])} <span aria-hidden="true">{arrow}</span></a>')
        rows.append(f'''<li class="news-entry">
          <div class="news-date"><time datetime="{date}">{date_label}</time><span>{escape(entry['category'])}</span></div>
          <div class="news-copy"><h3>{escape(entry['title'])}</h3><p>{escape(entry['text'])}</p><div class="news-links">{''.join(links)}</div></div>
        </li>''')
    recent = '<ol class="news-list">' + ''.join(rows[:5]) + '</ol>'
    if len(rows) > 5:
        recent += f'<details class="news-archive"><summary>More news <span>({len(rows)-5} earlier updates)</span></summary><ol class="news-list" start="6">' + ''.join(rows[5:]) + '</ol></details>'
    return recent

def render(groups, scholar, news=None):
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
    values['STYLE_VERSION'] = hashlib.sha256((ROOT/'stylesheet.css').read_bytes()).hexdigest()[:12]
    values['NEWS'] = render_news(news if news is not None else json.loads((ROOT/'data/news.json').read_text()))
    return re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], (ROOT/'templates/index.html').read_text())

def main():
    groups = json.loads((ROOT/'data/publications.json').read_text())
    scholar = json.loads((ROOT/'data/scholar.json').read_text())
    (ROOT/'index.html').write_text(render(groups,scholar))
    print(f'Rendered {sum(len(g["papers"]) for g in groups)} publications.')

if __name__ == '__main__':
    main()
