"""UI component helpers — single source of truth for the manuscript-warm design system.
All helpers return HTML strings rendered with st.markdown(unsafe_allow_html=True)."""
import os
import streamlit as st
import db
import i18n

CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.css')

def load_css():
    with open(CSS_PATH, encoding='utf-8') as f:
        css_core = f.read()
    pwa_html = '<link rel="manifest" href="manifest.json"><link rel="apple-touch-icon" href="icon.svg"><script>if("serviceWorker"in navigator){navigator.serviceWorker.register("sw.js")}</script>'
    st.markdown(f"<style>{css_core}</style>{pwa_html}", unsafe_allow_html=True)

# ---------------- chips & pills ----------------
def chip(text, color=None, cls='', aria_label=''):
    style = f"style='background:{color}'" if color else ''
    al = f" aria-label='{aria_label}'" if aria_label else ''
    return f"<span class='r-chip {cls}' {style}{al}>{text}</span>"

def verdict_chip(verdict, prefix=''):
    lab, col, em = db.reliability(verdict)
    lab = i18n.grade_label(lab)
    return chip(f"{em} {prefix}{lab}", col, aria_label=f'{prefix}{lab}')

def tabaqah_chip(t):
    """t = narrator_tabaqah row dict."""
    if not t: return ''
    mod = i18n.mod_name(t['modifier'] or '')
    txt = i18n.t('chip.tab', name=i18n.tab_name(t['tabaqa']))
    if mod: txt += i18n.t('chip.tab.mod', mod=mod)
    if t['tabaqah_high'] != t['tabaqah_low']:
        txt += i18n.t('chip.tab.span', lo=t['tabaqah_low'], hi=t['tabaqah_high'])
    return chip(f"🏷️ {txt}", cls='tab')

def pill(text):
    return f"<span class='r-pill'>{text}</span>"

# ---------------- cards ----------------
def card(html, cls=''):
    return f"<div class='r-card {cls}'>{html}</div>"

def quote(text):
    return f"<div class='r-quote'>{text}</div>"

def stat(num, label):
    return f"<div class='r-stat'><div class='num'>{num}</div><div class='lbl'>{label}</div></div>"

def statband(items):
    inner = ''.join(stat(n, l) for n, l in items)
    return f"<div class='r-statband'>{inner}</div>"

def tile(title, author, meta):
    return (f"<div class='r-tile'><div class='t'>{title}</div>"
            f"<div class='a'>{author or ''}</div><div class='m'>{meta}</div></div>")

def flagnote(text):
    return f"<div class='r-flagnote'>⚠ {text}</div>"

def narrator_row(d_id, name, verdict=None, tab=None, num=None):
    """Search/browse result row — opens the narrator profile in-app via the ?n= deep link."""
    em, lab = '', ''
    if verdict:
        l, c, e = db.reliability(verdict); em = e; lab = i18n.grade_label(l)
    meta = ' · '.join(x for x in ([lab] if lab else []) + ([i18n.t('chip.tab.short', n=tab)] if tab else []))
    n = f"{num}. " if num else ''
    return (f"<a class='r-row' href='?n={d_id}'>"
            f"<span class='nm2'>{n}{em} {i18n.disp_name(name, html=True)}</span><span class='meta'>{meta}</span></a>")

# ---------------- isnad stepper ----------------
def isnad_node(name, d_id=None, verdict=None, tab=None, is_imam=False, note=None):
    cls = 'isnad-node imam' if is_imam else ('isnad-node' if d_id else 'isnad-node unresolved')
    vch = verdict_chip(verdict) if verdict else (chip(i18n.t('p.masum'), 'var(--gold)') if is_imam else '')
    tch = f"<span class='r-sub'> {i18n.t('chip.tab.short', n=tab)}</span>" if tab else ''
    dn = i18n.disp_name(name, html=True)
    nm = (f"<a href='?n={d_id}' target='_self'>{dn}</a>" if d_id
          else f"<span style='color:var(--daif)'>{dn} <span class='r-sub'>{i18n.t('st.unresolved')}</span></span>")
    nnote = f" <span class='r-sub'>{note}</span>" if note else ''
    return f"<div class='{cls}'>{nm} {vch}{tch}{nnote}</div>"

def isnad_level(nodes_html, atf=False):
    atf_tag = f"<span class='isnad-atf'>{i18n.t('st.atf')}</span>" if atf else ''
    return f"<div class='isnad-level'>{''.join(nodes_html)}{atf_tag}</div>"

def isnad_conn(status, note='', chain_count=0):
    """status: 'ok' | 'bad' | 'warn' | 'none'."""
    if status == 'ok' and chain_count > 0:
        txt = i18n.t('st.conn.ok.n', n=f'{chain_count:,}')
    elif status == 'ok':
        txt = i18n.t('st.conn.ok')
    elif status == 'bad':
        txt = i18n.t('st.conn.bad')
    elif status == 'warn':
        txt = f'⚠ {note}'
    else:
        txt = '↓'
    cls = status if status in ('ok', 'bad', 'warn') else ''
    return f"<div class='isnad-conn {cls}'>{txt}</div>"

def grade_box(grade, color, why):
    return (f"<div class='r-grade' style='background:{color}'>{i18n.t('st.grade', g=grade)}"
            f"<span class='why'>{why}</span></div>")
