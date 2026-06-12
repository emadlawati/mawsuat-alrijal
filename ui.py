"""UI component helpers — single source of truth for the manuscript-warm design system.
All helpers return HTML strings rendered with st.markdown(unsafe_allow_html=True)."""
import os
import streamlit as st
import db

CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.css')

def load_css():
    with open(CSS_PATH, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- chips & pills ----------------
def chip(text, color=None, cls=''):
    style = f"style='background:{color}'" if color else ''
    return f"<span class='r-chip {cls}' {style}>{text}</span>"

def verdict_chip(verdict, prefix=''):
    lab, col, em = db.reliability(verdict)
    return chip(f"{em} {prefix}{lab}", col)

def tabaqah_chip(t):
    """t = narrator_tabaqah row dict."""
    if not t: return ''
    mod = db.MOD_AR.get(t['modifier'] or '', '')
    txt = f"الطبقة {db.TAB_AR.get(t['tabaqa'], t['tabaqa'])}"
    if mod: txt += f" (من {mod}ها)"
    if t['tabaqah_high'] != t['tabaqah_low']:
        txt += f" · أدرك الطبقات {t['tabaqah_low']}–{t['tabaqah_high']}"
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
    """Search/browse result row — opens the narrator profile in a NEW browser tab (?n= deep link)."""
    em, lab = '', ''
    if verdict:
        l, c, e = db.reliability(verdict); em = e; lab = l
    meta = ' · '.join(x for x in ([lab] if lab else []) + ([f'ط{tab}'] if tab else []))
    n = f"{num}. " if num else ''
    return (f"<a class='r-row' href='?n={d_id}' target='_blank' rel='noopener'>"
            f"<span class='nm2'>{n}{em} {name}</span><span class='meta'>{meta} ↗</span></a>")

# ---------------- isnad stepper ----------------
def isnad_node(name, d_id=None, verdict=None, tab=None, is_imam=False, note=None):
    cls = 'isnad-node imam' if is_imam else ('isnad-node' if d_id else 'isnad-node unresolved')
    vch = verdict_chip(verdict) if verdict else (chip('🌟 معصوم', 'var(--gold)') if is_imam else '')
    tch = f"<span class='r-sub'> ط{tab}</span>" if tab else ''
    nm = (f"<a href='?n={d_id}' target='_self'>{name}</a>" if d_id
          else f"<span style='color:var(--daif)'>{name} <span class='r-sub'>(لم يُحدَّد)</span></span>")
    nnote = f" <span class='r-sub'>{note}</span>" if note else ''
    return f"<div class='{cls}'>{nm} {vch}{tch}{nnote}</div>"

def isnad_level(nodes_html, atf=False):
    atf_tag = "<span class='isnad-atf'>(عطف — في الطبقة نفسها)</span>" if atf else ''
    return f"<div class='isnad-level'>{''.join(nodes_html)}{atf_tag}</div>"

def isnad_conn(status, note='', chain_count=0):
    """status: 'ok' | 'bad' | 'warn' | 'none'."""
    base = {'ok': '✓ ', 'bad': '⚠ ', 'warn': '⚠ ', 'none': '↓'}.get(status, '↓')
    if status == 'ok' and chain_count > 0:
        txt = f'{base}الرواية بينهما ثابتة (في {chain_count:,} سنداً)'
    elif status == 'ok':
        txt = f'{base}الرواية بينهما ثابتة'
    elif status == 'bad':
        txt = '⚠ لم تثبت رواية بينهما في الأسانيد'
    elif status == 'warn':
        txt = f'⚠ {note}'
    else:
        txt = '↓'
    cls = status if status in ('ok', 'bad', 'warn') else ''
    return f"<div class='isnad-conn {cls}'>{txt}</div>"

def grade_box(grade, color, why):
    return (f"<div class='r-grade' style='background:{color}'>حكم السند: {grade}"
            f"<span class='why'>{why}</span></div>")
