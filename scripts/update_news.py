import json, os, re, hashlib
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse, parse_qs
import feedparser

ROOT = os.path.dirname(os.path.dirname(__file__))
PUBLIC = os.path.join(ROOT, 'public')
CATEGORIES = os.path.join(PUBLIC, 'harm_categories.json')
SOURCES = os.path.join(PUBLIC, 'sources.json')
TRUSTED = os.path.join(PUBLIC, 'trusted_domains.json')
OUT = os.path.join(PUBLIC, 'news_data.json')
WINDOW = os.getenv('SCAN_WINDOW', '14d')
MAX_PER_CATEGORY = int(os.getenv('MAX_PER_CATEGORY', '18'))
MIN_SCORE = int(os.getenv('MIN_SCORE', '3'))

NOISE = ['stock', 'share price', 'earnings', 'funding round', 'valuation', 'appoints', 'partnership', 'conference agenda']

def load(path, fallback):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except Exception: return fallback

def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9\s-]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def parse_date(s):
    if not s: return datetime.now(timezone.utc)
    for fn in (parsedate_to_datetime, lambda x: datetime.fromisoformat(x.replace('Z','+00:00'))):
        try:
            d = fn(s)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception: pass
    return datetime.now(timezone.utc)

def canonical_url(url):
    if not url: return ''
    try:
        q = parse_qs(urlparse(url).query)
        if 'url' in q and q['url'] and q['url'][0].startswith('http'):
            return q['url'][0]
    except Exception: pass
    return url

def domain_of(url):
    try:
        host = urlparse(url).netloc.lower().split(':')[0]
        return host[4:] if host.startswith('www.') else host
    except Exception: return ''

def is_trusted(url, trusted):
    d = domain_of(url)
    return bool(d) and any(d == t or d.endswith('.' + t) for t in trusted)

def stable_id(text): return hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]

def score_text(text, cat):
    t = norm(text)
    if any(n in t for n in NOISE): return -99, []
    why=[]; score=0
    must = [norm(x) for x in cat.get('must', [])]
    should = [norm(x) for x in cat.get('should', [])]
    uk = [norm(x) for x in cat.get('uk_boost', [])]
    if not any(m and m in t for m in must): return 0, []
    score += 1; why.append('AI-related')
    matched_should = [x for x in should if x and x in t]
    if matched_should:
        score += min(7, len(matched_should) * 2)
        why.extend(matched_should[:5])
    matched_uk = [x for x in uk if x and x in t]
    if matched_uk:
        score += 3
        why.append('UK signal')
    return score, why

def google_query(cat):
    ai = ' OR '.join(f'"{x}"' for x in cat.get('must', [])[:6])
    harms = ' OR '.join(f'"{x}"' for x in cat.get('should', [])[:10])
    # Exclude common business-only noise in query as well as post-filter.
    return f'({ai}) ({harms}) -stock -shares -earnings when:{WINDOW}'

def google_url(cat):
    return 'https://news.google.com/rss/search?q=' + quote_plus(google_query(cat)) + '&hl=en-GB&gl=GB&ceid=GB:en'

def feed_items(url, source_name, source_type='news'):
    feed = feedparser.parse(url)
    for e in getattr(feed, 'entries', []) or []:
        title = getattr(e, 'title', '') or ''
        summary = re.sub('<[^<]+?>', '', getattr(e, 'summary', '') or getattr(e, 'description', '') or '')[:500]
        link = canonical_url(getattr(e, 'link', '') or '')
        published = parse_date(getattr(e, 'published', '') or getattr(e, 'updated', '') or '')
        yield {'title': title.rsplit(' - ', 1)[0].strip(), 'summary': summary, 'url': link, 'domain': domain_of(link), 'source': source_name, 'publishedAt': published.isoformat(), 'source_type': source_type}

def run():
    categories = load(CATEGORIES, {})
    sources = load(SOURCES, [])
    trusted = [x.lower() for x in load(TRUSTED, [])]
    all_items=[]; seen=set(); errors={}
    for cat_name, cat in categories.items():
        bucket=[]
        try:
            candidates = list(feed_items(google_url(cat), 'Google News', 'news'))
        except Exception as e:
            errors[f'Google News:{cat_name}'] = str(e); candidates=[]
        for src in sources:
            if not src.get('enabled') or src.get('type') != 'rss': continue
            try:
                candidates.extend(feed_items(src['url'], src.get('name','RSS'), 'rss'))
            except Exception as e:
                errors[src.get('name','RSS')] = str(e)
        for item in candidates:
            text = f"{item['title']} {item.get('summary','')} {item.get('source','')} {item.get('domain','')}"
            s, why = score_text(text, cat)
            if s < MIN_SCORE: continue
            # Avoid duplicate headlines across categories; first matching category in config wins.
            key = norm(item['title'])[:140] or item['url']
            if key in seen: continue
            seen.add(key)
            item.update({
                'id': stable_id(cat_name + item['title'] + item.get('url','')),
                'category': cat_name,
                'relevance_score': s,
                'why': why,
                'uk_relevant': 'UK signal' in why,
                'link_safe': is_trusted(item.get('url',''), trusted)
            })
            bucket.append(item)
        bucket.sort(key=lambda x: (x['relevance_score'], x['link_safe'], x['publishedAt']), reverse=True)
        all_items.extend(bucket[:MAX_PER_CATEGORY])
    all_items.sort(key=lambda x: (x['publishedAt'], x['relevance_score']), reverse=True)
    meta = {'ok': True, 'generatedAt': datetime.now(timezone.utc).replace(microsecond=0).isoformat(), 'total': len(all_items), 'window': WINDOW, 'minScore': MIN_SCORE, 'byCategory': dict(Counter(i['category'] for i in all_items)), 'feedbackApplied': True, 'linkPolicy': 'Direct links only shown for domains in public/trusted_domains.json', 'errors': errors}
    os.makedirs(PUBLIC, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f: json.dump({'meta': meta, 'articles': all_items}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT} with {len(all_items)} items")

if __name__ == '__main__': run()
