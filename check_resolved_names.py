#!/usr/bin/env python3
"""Check resolved MMS object-reference lengths for every FCDA and RCB in an SCL
file, independent of XSD schema validation.

Why this exists: the SCL schema validates each name attribute (LDName,
prefix+lnClass+lnInst, DataName, sub-attribute names) against its own
individual maximum length. It does NOT check the assembled object reference
that a server/client actually builds and exchanges on the wire:

    LDName/LNName$FC$DataName$DataAttrName[.subDA...]   (IEC 61850-8-1 Annex G)
    LDName/LNName$FC$RCBName                             (RCB reference)

A file can therefore be 100% schema-valid while producing an object
reference that exceeds the ACSI-mapped limit (commonly cited as 129
characters total, including separators -- see IEC 61850-7-2 clause 22.2 and
IEC 61850 Tissue 141). This script reports the resolved length so you can
catch that gap before it reaches a real server/client.

Usage: python3 check_resolved_names.py file.icd [--max-ref 129] [--max-rcb 64]
"""
import argparse
import sys
import xml.etree.ElementTree as ET

ap = argparse.ArgumentParser()
ap.add_argument("icd")
ap.add_argument("--max-ref", type=int, default=129, help="max length for LDName/LNName$FC$DataName$DA[...] ")
ap.add_argument("--max-rcb", type=int, default=65, help="max length for LDName/LNName$FC$RCBName (64 + '/' style check)")
a = ap.parse_args()

N = "{http://www.iec.ch/61850/2003/SCL}"
root = ET.parse(a.icd).getroot()

rows = []
bad = 0

for ld in root.iter(N + "LDevice"):
    ldinst = ld.get("inst") or ""
    lns = list(ld.iter(N + "LN")) + list(ld.iter(N + "LN0"))
    for ln in lns:
        for ds in ln.iter(N + "DataSet"):
            for f in ds.iter(N + "FCDA"):
                prefix = f.get("prefix") or ""
                lnclass = f.get("lnClass") or ""
                lninst = f.get("lnInst") or ""
                fc = f.get("fc") or ""
                do = f.get("doName") or ""
                da = f.get("daName") or ""
                lnname = f"{prefix}{lnclass}{lninst}"
                ref = f"{f.get('ldInst', ldinst)}/{lnname}${fc}${do}" + (f"${da}" if da else "")
                mms_ref = ref.replace(".", "$")  # on the wire, sub-components use '$' too in some mappings
                status = "OK" if len(ref) <= a.max_ref else "TOO LONG"
                if status != "OK":
                    bad += 1
                rows.append(("FCDA", ref, len(ref), status))
        for rcb in list(ln.iter(N + "ReportControl")):
            name = rcb.get("name") or ""
            rptid = rcb.get("rptID") or ""
            datset = rcb.get("datSet") or ""
            lnname = f"{ln.get('prefix') or ''}{ln.get('lnClass') or ''}{ln.get('inst') or ''}"
            rcb_ref = f"{ldinst}/{lnname}$BR${name}" if rcb.get("buffered") == "true" else f"{ldinst}/{lnname}$RP${name}"
            status = "OK" if len(rcb_ref) <= a.max_rcb else "TOO LONG"
            if status != "OK":
                bad += 1
            rows.append(("RCB", rcb_ref, len(rcb_ref), status))
            status2 = "OK" if len(rptid) <= 129 else "TOO LONG"
            if status2 != "OK":
                bad += 1
            rows.append(("RptID", rptid, len(rptid), status2))
            status3 = "OK" if len(datset) <= 129 else "TOO LONG"
            if status3 != "OK":
                bad += 1
            rows.append(("DatSet ref", datset, len(datset), status3))

w = max((len(r[1]) for r in rows), default=20)
print(f"{'kind':10s} {'resolved reference':{w}s} len  status")
for kind, ref, ln, status in rows:
    marker = " <-- " if status != "OK" else "     "
    print(f"{kind:10s} {ref:{w}s} {ln:4d}{marker}{status}")

print()
print(f"{bad} of {len(rows)} resolved reference(s) exceed the checked limit.")
sys.exit(1 if bad else 0)
