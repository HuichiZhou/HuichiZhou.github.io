'use strict';
const search = document.querySelector('#publication-search');
const topic = document.querySelector('#topic-filter');
const groups = [...document.querySelectorAll('.publication-group')];
const papers = [...document.querySelectorAll('.paper')];
const status = document.querySelector('#search-status');
const normalize = value => value.normalize('NFKD').toLowerCase().replace(/[\u0300-\u036f]/g, '');
const searchText = new Map(papers.map(paper => [paper, normalize(paper.dataset.search)]));
let savedOpen = null;
function filterPublications() {
  const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
  const active = terms.length > 0 || topic.value !== 'all';
  if (active && !savedOpen) savedOpen = new Map(groups.map(group => [group, group.open]));
  let visible = 0;
  for (const group of groups) {
    let count = 0;
    for (const paper of group.querySelectorAll('.paper')) {
      const matches = (topic.value === 'all' || group.dataset.topic === topic.value) && terms.every(term => searchText.get(paper).includes(term));
      paper.hidden = !matches;
      if (matches) count++;
    }
    group.hidden = count === 0;
    group.querySelector('.group-count').textContent = `${count} ${count === 1 ? 'paper' : 'papers'}`;
    if (active && count) group.open = true;
    else if (!active && savedOpen) group.open = savedOpen.get(group);
    visible += count;
  }
  if (!active) savedOpen = null;
  status.textContent = active ? `${visible} of ${papers.length} publications` : `${papers.length} publications across ${groups.length} research areas`;
  document.querySelector('#no-results').hidden = visible !== 0;
}
document.querySelector('.publication-tools').hidden = false;
status.hidden = false;
search.addEventListener('input', filterPublications);
topic.addEventListener('change', filterPublications);
document.querySelector('#clear-search').addEventListener('click', () => { search.value=''; topic.value='all'; filterPublications(); search.focus(); });
filterPublications();

// Optional enhancement: citation data is already present in the HTML.
async function repoStars(element) {
  const repo = element.dataset.repo;
  const key = `repo-stars:${repo}`;
  let cached;
  try { cached = JSON.parse(localStorage.getItem(key)); } catch { /* Storage may be unavailable. */ }
  const show = count => { element.textContent = `★ ${count.toLocaleString('en-GB')}`; };
  if (Number.isInteger(cached?.count)) show(cached.count);
  if (cached && Date.now()-cached.at < 86400000) return;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(),5000);
  try {
    const response = await fetch(`https://api.github.com/repos/${repo}`,{signal:controller.signal});
    if (!response.ok) return;
    const data = await response.json();
    if (!Number.isInteger(data.stargazers_count)) return;
    show(data.stargazers_count);
    try { localStorage.setItem(key,JSON.stringify({count:data.stargazers_count,at:Date.now()})); } catch { /* Optional cache. */ }
  } catch { /* The Code link remains usable without a star count. */ }
  finally { clearTimeout(timeout); }
}
document.querySelectorAll('.github-stars').forEach(repoStars);
