"""Experimental personal-use alerts. Yahoo data is unofficial; no execution."""
import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
import urllib.request

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo('America/New_York')
TR = ZoneInfo('Europe/Istanbul')


def pivots(rows, column, high=True):
    result = []
    for i in range(2, len(rows) - 2):
        value = rows[i][column]
        neighbors = [rows[j][column] for j in (i-2, i-1, i+1, i+2)]
        if (high and value > max(neighbors)) or (not high and value < min(neighbors)):
            result.append((i, value))
    return result


def analyze(rows, historical_highs, approach_pct=3):
    # Only confirmed pivots: two later COMPLETED bars required. No future bars used.
    if len(rows) < 8:
        return None
    peaks = pivots(rows[:-1], 'high')
    if not peaks:
        return None
    index, level = peaks[-1]
    latest = rows[-1]
    # A level already exceeded in an earlier bar is consumed, not a new signal.
    if any(r['high'] > level for r in rows[index+1:-1]):
        return None
    lows = [r['low'] for r in rows[index+1:-1]]
    stop = min(lows) if lows else None
    if stop is None or stop >= level:
        return None
    breakout = latest['close'] > level and rows[-2]['close'] <= level
    near = level * (1 - approach_pct / 100) <= latest['close'] <= level
    if not (breakout or near):
        return None
    resistances = []
    for value in sorted(historical_highs + [v for _, v in peaks]):
        if value > level * 1.002 and (not resistances or value > resistances[-1] * 1.005):
            resistances.append(value)
    return dict(kind='KIRILIM' if breakout else 'YAKLAŞMA', level=level,
                price=latest['close'], stop=stop, resistances=resistances[:2],
                timestamp=latest['timestamp'], volume=latest['volume'])


def headline_assessment(title):
    # Conservative headline hints, not financial/news fact verification.
    text = title.lower()
    negative = [r'\bpublic offering\b', r'\bregistered direct offering\b',
                r'\bbankrupt\w*\b', r'\bdelisting\b', r'\btrial fail\w*\b',
                r'\bmisses estimates\b', r'\breverse (stock )?split\b']
    positive = [r'\bfda approv\w*\b', r'\bwins? .*contract\b',
                r'\bbeats estimates\b', r'\bregains .*compliance\b',
                r'\braises .*guidance\b']
    pos = [p for p in positive if re.search(p, text)]
    neg = [p for p in negative if re.search(p, text)]
    label = 'KARIŞIK' if pos and neg else 'OLUMSUZ İPUCU' if neg else 'OLUMLU İPUCU' if pos else 'BELİRSİZ'
    return label + ' — başlıkta anahtar ifade eşleşmesi; tam metin doğrulanmadı.'


def news_summary(items, now):
    recent = []
    for item in items:
        content = item.get('content', item)
        stamp = content.get('pubDate')
        try:
            published = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        except (AttributeError, ValueError):
            continue
        if not 0 <= (now - published).total_seconds() <= 86400:
            continue
        url = (content.get('canonicalUrl') or {}).get('url', '')
        title = content.get('title', 'Başlık yok')
        recent.append(f"{headline_assessment(title)}\n{title}\n{stamp}\n{url}")
    if not recent:
        return 'Son 24 saatte kaynakta doğrulanabilen haber bulunamadı; haber yok demek değildir.'
    return 'ÖN DEĞERLENDİRME (haber etkisi veya fiyat yönü garantisi değil):\n' + '\n'.join(recent[:2])


def format_alert(symbol, session, signal, age, news):
    r = signal['resistances']
    r1 = f'{r[0]:.4f}' if r else 'Belirlenemedi'
    r2 = f'{r[1]:.4f}' if len(r) > 1 else 'Belirlenemedi'
    return (f"DENEYSEL | {symbol} | {session} | {signal['kind']}\n"
            f"Kırılım seviyesi: {signal['level']:.4f} $\n"
            f"Son tamamlanan mum kapanışı: {signal['price']:.4f} $\n"
            f"R1: {r1} | R2: {r2}\n"
            f"Stop adayı (geri çekilme dibi): {signal['stop']:.4f} $\n"
            f"Mum hacmi: {signal['volume']:,}\n"
            f"Mum saati TR: {signal['timestamp'].astimezone(TR):%Y-%m-%d %H:%M}\n"
            f"Veri yaşı: {age:.0f} sn; anlık fiyat ve işlem garantisi yok.\n"
            f"Haber: {news}\n"
            'Kaynak: Yahoo Finance / yfinance, ücretsiz ve resmî olmayan veri. '
            'R1/R2 son 6 aylık teyitli günlük tepelerden; hedef getiri değildir.')


def telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        raise RuntimeError('Telegram gizli ayarları eksik')
    request = urllib.request.Request('https://api.telegram.org/bot' + token + '/sendMessage',
        data=json.dumps(dict(chat_id=chat, text=message[:4000], link_preview_options={'is_disabled': True})).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not result.get('ok'):
            raise RuntimeError('Telegram mesajı gönderilemedi')
    except Exception:
        # Never propagate a URL containing the credential into logs.
        raise RuntimeError('Telegram gönderimi başarısız; ayrıntılar gizlendi') from None


def scan(dry_run=False):
    import yfinance as yf
    import exchange_calendars as xcals
    import pandas as pd
    cfg = json.loads((ROOT / 'config.json').read_text())
    now = datetime.now(timezone.utc)
    local = now.astimezone(NY)
    cal = xcals.get_calendar('XNYS')
    day = pd.Timestamp(local.date())
    if not cal.is_session(day):
        print('Piyasa günü değil; sinyal üretilmedi.')
        return
    opening = cal.session_open(day).to_pydatetime()
    closing = cal.session_close(day).to_pydatetime()
    if local.time() < time(4) or now >= closing:
        print('Takip seansı dışında; sinyal üretilmedi.')
        return
    session = 'PREMARKET' if now < opening else 'NORMAL SEANS'
    start = datetime.combine(local.date(), time(4), NY) if now < opening else opening
    state_path = ROOT / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state.get('date') != str(local.date()):
        state = {'date': str(local.date()), 'sent': []}
    query = yf.EquityQuery('and', [
        yf.EquityQuery('is-in', ['exchange', 'NMS', 'NGM', 'NCM']),
        yf.EquityQuery('btwn', ['intradayprice', cfg['min_price'], cfg['max_price']])])
    # Discovery may reflect regular-session quotes: premarket coverage is incomplete.
    candidates = yf.screen(query, size=100, sortField='percentchange', sortAsc=False)
    symbols = list(dict.fromkeys(cfg['watchlist'] +
        [q['symbol'] for q in candidates.get('quotes', []) if q.get('quoteType') == 'EQUITY']))[:cfg['max_candidates']]
    counts = dict(candidates=len(symbols), alerts=0, stale=0, failures=0)
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            frame = ticker.history(period='5d', interval='1m', prepost=True, auto_adjust=True)
            if frame.empty:
                counts['failures'] += 1
                continue
            frame = frame[frame.index + pd.Timedelta(minutes=1) <= now]
            today = frame[frame.index >= start]
            if today.empty:
                continue
            age = (now - (today.index[-1].to_pydatetime() + pd.Timedelta(minutes=1))).total_seconds()
            if age > cfg['max_data_age_seconds']:
                counts['stale'] += 1
                continue
            if today.Volume.sum() < cfg['min_session_volume']:
                continue
            daily = ticker.history(period='6mo', interval='1d', auto_adjust=True)
            prior = daily[[d.date() < local.date() for d in daily.index]]
            if prior.empty:
                continue
            price = float(today.Close.iloc[-1])
            if not cfg['min_price'] <= price <= cfg['max_price']:
                continue
            if (price / float(prior.Close.iloc[-1]) - 1) * 100 < cfg['min_gain_pct']:
                continue
            rows = [dict(timestamp=i.to_pydatetime(), high=float(r.High), low=float(r.Low),
                         close=float(r.Close), volume=int(r.Volume)) for i, r in today.iterrows()]
            old_rows = [dict(high=float(r.High)) for _, r in prior.iterrows()]
            signal = analyze(rows, [v for _, v in pivots(old_rows, 'high')], cfg['approach_pct'])
            if not signal:
                continue
            key = f"{symbol}:{session}:{signal['level']:.4f}:{signal['kind']}"
            if key in state['sent']:
                continue
            try:
                news = news_summary(ticker.get_news(count=10), now)
            except Exception:
                news = 'Haber kaynağına erişilemedi; değerlendirme yapılamadı.'
            message = format_alert(symbol, session, signal, age, news)
            if dry_run:
                print(message)
            else:
                telegram(message)
                state['sent'].append(key)
                state_path.write_text(json.dumps(state), encoding='utf-8')
            counts['alerts'] += 1
        except Exception:
            counts['failures'] += 1
            print(f'{symbol}: veri/işlem hatası; gizli ayrıntılar yazılmadı.')
    print(json.dumps(counts))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    scan(args.dry_run)
