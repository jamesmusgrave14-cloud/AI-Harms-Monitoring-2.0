import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function useJson(path) {
  const [state, setState] = useState({ loading: true, error: '', data: null });
  useEffect(() => {
    fetch(path, { cache: 'no-store' })
      .then(async r => {
        if (!r.ok) throw new Error(`${path} returned ${r.status}`);
        return r.json();
      })
      .then(data => setState({ loading: false, error: '', data }))
      .catch(e => setState({ loading: false, error: e.message, data: null }));
  }, [path]);
  return state;
}

function fmtDate(value) {
  if (!value) return 'No date';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
}

function App() {
  const news = useJson('/news_data.json');
  const cats = useJson('/harm_categories.json');
  const [category, setCategory] = useState('All');
  const [onlyUk, setOnlyUk] = useState(false);
  const [safeLinksOnly, setSafeLinksOnly] = useState(false);
  const [minScore, setMinScore] = useState(3);
  const [q, setQ] = useState('');

  const articles = useMemo(() => Array.isArray(news.data?.articles) ? news.data.articles : [], [news.data]);
  const categories = useMemo(() => ['All', ...Object.keys(cats.data || {})], [cats.data]);
  const filtered = useMemo(() => articles.filter(a => {
    if (category !== 'All' && a.category !== category) return false;
    if (onlyUk && !a.uk_relevant) return false;
    if (safeLinksOnly && !a.link_safe) return false;
    if ((a.relevance_score || 0) < minScore) return false;
    if (q && !`${a.title} ${a.summary} ${a.source} ${a.domain}`.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  }), [articles, category, onlyUk, safeLinksOnly, minScore, q]);

  const meta = news.data?.meta || {};
  return <main className="wrap">
    <header className="hero">
      <div>
        <p className="kicker">Static · GitHub Pages · feedback-aligned</p>
        <h1>AI Harms Monitor</h1>
        <p>Curated horizon scanning with separated VAWG/NCII views, UK boost, relevance scoring and safer link handling.</p>
      </div>
      <div className="metric"><b>{filtered.length}</b><span>shown</span></div>
    </header>

    <section className="stats">
      <div><span>Total results</span><b>{articles.length}</b></div>
      <div><span>UK-relevant</span><b>{articles.filter(a => a.uk_relevant).length}</b></div>
      <div><span>Safe direct links</span><b>{articles.filter(a => a.link_safe).length}</b></div>
      <div><span>Updated</span><b>{meta.generatedAt ? fmtDate(meta.generatedAt) : 'Not yet'}</b></div>
    </section>

    <section className="filters">
      <select value={category} onChange={e => setCategory(e.target.value)}>{categories.map(c => <option key={c}>{c}</option>)}</select>
      <label><input type="checkbox" checked={onlyUk} onChange={e => setOnlyUk(e.target.checked)} /> UK-relevant only</label>
      <label><input type="checkbox" checked={safeLinksOnly} onChange={e => setSafeLinksOnly(e.target.checked)} /> safe direct links only</label>
      <label>Min score <input type="number" min="0" max="20" value={minScore} onChange={e => setMinScore(Number(e.target.value || 0))} /></label>
      <input placeholder="Search shown results…" value={q} onChange={e => setQ(e.target.value)} />
    </section>

    {news.error && <p className="error">Could not load results: {news.error}</p>}
    {news.loading && <p className="notice">Loading…</p>}
    {meta.linkPolicy && <p className="notice small">{meta.linkPolicy}</p>}

    <section className="list">
      {filtered.map((a, i) => <article className="item" key={a.id || a.url || i}>
        <div>
          <p className="cat">{a.category}</p>
          <h2>{a.title}</h2>
          {a.summary && <p className="summary">{a.summary}</p>}
          <p className="meta">{a.source}{a.domain ? ` · ${a.domain}` : ''} · {fmtDate(a.publishedAt)} · score {a.relevance_score ?? 0}{a.uk_relevant ? ' · UK-relevant' : ''}{a.link_safe ? ' · direct link allowed' : ' · link not allowlisted'}</p>
          {Array.isArray(a.why) && a.why.length > 0 && <p className="why">Why included: {a.why.join(', ')}</p>}
        </div>
        {a.url && a.link_safe ? <a className="open" href={a.url} target="_blank" rel="noreferrer">Open</a> : <span className="blocked" title="Search the headline manually if needed">No direct link</span>}
      </article>)}
      {!news.loading && filtered.length === 0 && <p className="notice">No results match these filters. Lower the score threshold or run the scraper.</p>}
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
