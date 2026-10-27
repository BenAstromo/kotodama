import gzip, pickle, xml.etree.ElementTree as ET
XL='{http://www.w3.org/XML/1998/namespace}lang'
entries={}
with gzip.open("JMdict_e.gz") as f:
    for ev, el in ET.iterparse(f, events=("end",)):
        if el.tag!="entry": continue
        seq=int(el.findtext("ent_seq"))
        keb=[k.findtext("keb") for k in el.findall("k_ele")]
        reb=[r.findtext("reb") for r in el.findall("r_ele")]
        langs=[]; wasei=False; misc=[]; pos=[]
        for s in el.findall("sense"):
            sm=[m.text for m in s.findall("misc")]; misc.append(sm)
            # Part of speech (entity text, e.g. "interjection (kandoushi)");
            # build_freq.py matches it against the corpus POS.
            for p in s.findall("pos"):
                if p.text not in pos: pos.append(p.text)
            for ls in s.findall("lsource"):
                langs.append(ls.get(XL,"eng"))
                if ls.get("ls_wasei")=="y": wasei=True
        entries[seq]=dict(keb=keb,reb=reb,langs=langs,wasei=wasei,misc=misc,pos=pos)
        el.clear()
pickle.dump(entries, open("jmdict.pkl","wb"))
print(len(entries))
