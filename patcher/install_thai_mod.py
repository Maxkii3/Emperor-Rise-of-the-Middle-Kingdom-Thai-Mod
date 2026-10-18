#!/usr/bin/env python3
"""
Emperor: Rise of the Middle Kingdom - Thai Mod installer / ตัวติดตั้ง mod ภาษาไทย

Usage / วิธีใช้:
    python install_thai_mod.py "D:\\Sierra\\Emperor"            # install
    python install_thai_mod.py "D:\\Sierra\\Emperor" --uninstall  # restore originals

Requires Python 3.8+ (standard library only).
Works on an installed copy of Emperor v1.0.1.0 (English).
Original files are backed up to <game>\\_ThaiMod_backup before anything is changed.
"""
import json, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
ROOT = os.path.dirname(HERE)
TR = os.path.join(ROOT, 'translations')

FILES = ['Emperor.exe', 'EmperorText.eng', 'EmperorMM.eng',
         os.path.join('DATA', 'China_Fonts.sg3'), os.path.join('DATA', 'China_Fonts.555'),
         os.path.join('Model', 'EmperorEventmsg.txt'), os.path.join('Model', 'Proverbs.txt')]

# ----------------------------------------------------------------------------
# Thai text encoder (Unicode Thai -> the game's single-byte Thai code page)
# ----------------------------------------------------------------------------
UPPER = set('\u0E31\u0E34\u0E35\u0E36\u0E37\u0E47\u0E4D\u0E4E')
TONE = set('\u0E48\u0E49\u0E4A\u0E4B\u0E4C')
LOWER = set('\u0E38\u0E39\u0E3A')
TONES = ['\u0E48', '\u0E49', '\u0E4A', '\u0E4B', '\u0E4C']
UPPERS = ['\u0E31', '\u0E34', '\u0E35', '\u0E36', '\u0E37', '\u0E47', '\u0E4D']
UNI2CP = {chr(0x0E00 + c - 0xA0): c for c in range(0xA1, 0xFC)}
HIGH = {t: 0x80 + i for i, t in enumerate(TONES)}      # tone above an upper vowel
LEFTU = {u: 0x85 + i for i, u in enumerate(UPPERS)}    # upper vowel shifted left (after ป ฝ ฟ ฬ)
LEFTL = {t: 0x8C + i for i, t in enumerate(TONES)}     # low tone shifted left
LEFTH = {t: 0x91 + i for i, t in enumerate(TONES)}     # high tone shifted left
TALL = set('\u0E1B\u0E1D\u0E1F\u0E2C')
REPL = {'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-',
        '\u2014': '-', '\u2026': '...', '\u00a0': ' '}


def encode(s):
    s = s.replace('\u0E4D\u0E32', '\u0E33')
    out = bytearray(); i = 0; n = len(s)
    marks_all = UPPER | TONE | LOWER | {'\u0E33'}
    while i < n:
        ch = s[i]
        if ord(ch) < 0x80:
            out.append(ord(ch)); i += 1; continue
        if '\u0E00' <= ch <= '\u0E7F' and ch not in marks_all:
            base = ch; i += 1; marks = []
            while i < n and s[i] in marks_all:
                marks.append(s[i]); i += 1
            am = '\u0E33' in marks
            marks = [m for m in marks if m != '\u0E33']
            if am:
                marks = ['\u0E4D'] + marks
            tall = base in TALL
            out.append(UNI2CP[base])
            hasup = any(m in UPPER for m in marks)
            for m in marks:
                if m in UPPER:
                    out.append(LEFTU[m] if tall else UNI2CP[m])
                elif m in TONE:
                    if tall:
                        out.append(LEFTH[m] if hasup else LEFTL[m])
                    else:
                        out.append(HIGH[m] if hasup else UNI2CP[m])
                else:
                    out.append(UNI2CP[m])
            if am:
                out.append(UNI2CP['\u0E32'])
            continue
        if ch in UPPER | TONE | LOWER:
            out.append(UNI2CP.get(ch, 63)); i += 1; continue
        out += REPL.get(ch, '?').encode('ascii'); i += 1
    return bytes(out)


def load_tr(name):
    return {x['id']: x['th'] for x in json.load(open(os.path.join(TR, name), encoding='utf-8'))}


# ----------------------------------------------------------------------------
# EmperorText.eng
# ----------------------------------------------------------------------------
def build_text(src):
    d = open(src, 'rb').read()
    if d[:16] != b'Emperor textfile':
        raise SystemExit('EmperorText.eng: unexpected file')
    IDX = 0x1c; base = IDX + 8000
    idx = [struct.unpack('<2I', d[IDX + i * 8:IDX + 8 + i * 8]) for i in range(1000)]
    text = d[base:]
    groups = {}
    for g, (o, c) in enumerate(idx):
        if not c:
            continue
        p = o; arr = []
        for _ in range(c):
            e = text.index(b'\0', p); arr.append(text[p:e]); p = e + 1
        groups[g] = arr
    for key, val in load_tr('EmperorText.th.json').items():
        g, i = map(int, key[1:].split(':'))
        groups[g][i] = encode(val)
    blob = bytearray(); newidx = []
    for g in range(1000):
        o, c = idx[g]
        if c:
            newidx.append((len(blob), c)); blob += b''.join(s + b'\0' for s in groups[g])
        else:
            newidx.append((0, 0))
    return d[:IDX] + b''.join(struct.pack('<2I', *e) for e in newidx) + bytes(blob)


# ----------------------------------------------------------------------------
# EmperorMM.eng (help pages and messages)
# ----------------------------------------------------------------------------
def build_mm(src):
    d = open(src, 'rb').read()
    if d[:15] != b'Emperor MM file' or len(d) != 422806:
        raise SystemExit('EmperorMM.eng: this mod needs the v1.0.1.0 English EmperorMM.eng')
    B = 0x13898; blob = d[B:]; ents = bytearray(d[24:B])
    ptrs = set()
    for e in range(1000):
        f = struct.unpack_from('<20I', ents, e * 80)
        for k in (17, 18, 19):
            if f[k]:
                ptrs.add(f[k])
    tr = load_tr('EmperorMM.th.json')
    ps = sorted(ptrs); nb = bytearray(blob[:ps[0]]); mp = {}
    for p in ps:
        s = blob[p:blob.index(b'\0', p)]
        if 'M%d' % p in tr:
            s = encode(tr['M%d' % p])
        mp[p] = len(nb); nb += s + b'\0'
    for e in range(1000):
        for k in (17, 18, 19):
            v = struct.unpack_from('<I', ents, e * 80 + k * 4)[0]
            if v:
                struct.pack_into('<I', ents, e * 80 + k * 4, mp[v])
    return d[:24] + bytes(ents) + bytes(nb)


# ----------------------------------------------------------------------------
# Model\EmperorEventmsg.txt (event / advisor messages) and Model\Proverbs.txt
# ----------------------------------------------------------------------------
def build_eventmsg(src):
    import re
    tr = load_tr('EmperorEventmsg.th.json')
    out = []
    for line in open(src, 'rb').read().split(b'\r\n'):
        m = re.match(rb'(\s*)(PHRASE_\S+)(\s+)"(.*)"(\s*)$', line)
        if m:
            key = m.group(2).decode('ascii')
            if key in tr:
                line = m.group(1) + m.group(2) + m.group(3) + b'"' + encode(tr[key]) + b'"' + m.group(5)
        out.append(line)
    return b'\r\n'.join(out)


def build_proverbs(src):
    tr = load_tr('Proverbs.th.json')
    out = []
    for i, line in enumerate(open(src, 'rb').read().split(b'\r\n')):
        key = 'P%d' % i
        out.append(encode(tr[key]) if key in tr else line)
    return b'\r\n'.join(out)


# ----------------------------------------------------------------------------
# China_Fonts.sg3 / .555 : append 108 Thai glyphs to each of the 30 fonts
# ----------------------------------------------------------------------------
def build_fonts(sg_path, px_path):
    sg = open(sg_path, 'rb').read(); px = open(px_path, 'rb').read()
    IMG0 = 40680
    hdr = bytearray(sg[:IMG0])
    if struct.unpack('<I', hdr[16:20])[0] != 4220:
        raise SystemExit('China_Fonts.sg3: unexpected file (already modded?)')
    meta = json.load(open(os.path.join(DATA, 'thai_glyphs.json')))
    gblob = open(os.path.join(DATA, 'thai_glyphs.bin'), 'rb').read()
    codes = meta['codes']; OLD = meta['old_per_font']; NEW = OLD + len(codes); NB = 30
    glyphs = {(g[0], g[1]): g for g in meta['glyphs']}
    rec = lambda i: sg[IMG0 + i * 64:IMG0 + i * 64 + 64]
    tbl_H = 34  # glyph index of 'H' (template record for colours/flags)
    items = []
    for b in range(NB):
        for i in range(201 + b * OLD, 201 + (b + 1) * OLD):
            r = bytearray(rec(i)); o, l = struct.unpack('<2I', r[:8]); items.append((r, px[o:o + l]))
        tmpl = rec(201 + b * OLD + tbl_H - 1)
        for c in codes:
            _, _, w, h, ox, oy, adv, off, ln = glyphs[(b, c)]
            r = bytearray(tmpl)
            struct.pack_into('<hh', r, 20, w, h)
            struct.pack_into('<hhhh', r, 0x26, ox, oy, adv, 1)
            items.append((r, gblob[off:off + ln]))
    start = struct.unpack('<I', rec(201)[:4])[0]
    out555 = bytearray(px[:start]); recs = [rec(i) for i in range(201)]
    for r, data in items:
        struct.pack_into('<3I', r, 0, len(out555), len(data), len(data))
        out555 += data; recs.append(bytes(r))
    n = len(recs) - 1
    recs += [bytes(64)] * (10001 - len(recs))
    struct.pack_into('<I', hdr, 16, n)
    grp = list(struct.unpack('<300H', sg[80:680]))
    grp = [201 + ((g - 201) // OLD) * NEW if g >= 201 else g for g in grp]
    struct.pack_into('<300H', hdr, 80, *grp)
    b1s = 201; b1e = 201 + 18 * NEW - 1
    struct.pack_into('<3I', hdr, 680 + 200 * 1 + 124, b1e - b1s + 1, b1s, b1e)
    struct.pack_into('<3I', hdr, 680 + 200 * 2 + 124, n - b1e, b1e + 1, n)
    added = len(out555) - len(px)
    tot, f555 = struct.unpack('<II', hdr[28:36]); struct.pack_into('<II', hdr, 28, tot + added, f555 + added)
    out_sg = bytes(hdr) + b''.join(recs) + sg[IMG0 + 10001 * 64:]
    assert len(out_sg) == len(sg)
    return out_sg, bytes(out555)


# ----------------------------------------------------------------------------
# Emperor.exe : Thai glyph placement (combining vowels / tone marks)
# ----------------------------------------------------------------------------
def patch_exe(path):
    d = bytearray(open(path, 'rb').read())
    p = json.load(open(os.path.join(DATA, 'exe_patch.json')))
    if len(d) != p['size']:
        raise SystemExit('Emperor.exe: this mod needs Emperor v1.0.1.0 (size %d, found %d)' % (p['size'], len(d)))
    for r in p['patches']:
        o = r['off']; orig = bytes.fromhex(r['orig']); new = bytes.fromhex(r['new'])
        cur = bytes(d[o:o + len(orig)])
        if cur not in (orig, new):
            raise SystemExit('Emperor.exe: unexpected code at 0x%x - not a v1.0.1.0 English exe?' % o)
        d[o:o + len(new)] = new
    return bytes(d)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    game = sys.argv[1]
    bk = os.path.join(game, '_ThaiMod_backup')
    if '--uninstall' in sys.argv:
        for f in FILES:
            s = os.path.join(bk, f)
            if os.path.exists(s):
                shutil.copy2(s, os.path.join(game, f))
        print('Restored original files. / คืนไฟล์ต้นฉบับเรียบร้อย'); return
    for f in FILES:
        if not os.path.exists(os.path.join(game, f)):
            raise SystemExit('Not found: ' + os.path.join(game, f))
    for f in FILES:  # back up originals once
        dst = os.path.join(bk, f)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(game, f), dst)
    src = lambda f: os.path.join(bk, f)  # always build from the originals
    exe = patch_exe(src('Emperor.exe'))
    txt = build_text(src('EmperorText.eng'))
    mm = build_mm(src('EmperorMM.eng'))
    sg, px = build_fonts(src(FILES[3]), src(FILES[4]))
    ev = build_eventmsg(src(FILES[5]))
    pv = build_proverbs(src(FILES[6]))
    for f, data in zip(FILES, (exe, txt, mm, sg, px, ev, pv)):
        open(os.path.join(game, f), 'wb').write(data)
    print('Thai mod installed! / ติดตั้ง mod ภาษาไทยเรียบร้อย')


if __name__ == '__main__':
    main()
