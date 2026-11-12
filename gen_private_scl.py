#!/usr/bin/env python3
"""Generate a stress-test IEC 61850 SCL (ICD) with many private LNs/DOs.

Usage: python3 gen_private_scl.py [--classes 20] [--insts 5] [--dos 60]
                                  [--std-mmxu 5] [--std-priv-dos 50]
                                  [--ds-members 40] [-o out.icd]
Defaults give 100 private LNs x 60 DOs, 5 standard MMXU with 50 private DOs each.
"""
import argparse
import itertools
import string
from xml.sax.saxutils import quoteattr

ap = argparse.ArgumentParser()
ap.add_argument("--classes", type=int, default=20, help="number of private LN classes")
ap.add_argument("--insts", type=int, default=5, help="instances per private class")
ap.add_argument("--dos", type=int, default=60, help="DOs per private LN type (>=4 std + rest private)")
ap.add_argument("--std-mmxu", type=int, default=5, help="standard MMXU instances")
ap.add_argument("--std-priv-dos", type=int, default=50, help="private DOs added to the MMXU type")
ap.add_argument("--ds-members", type=int, default=40, help="max FCDAs per dataset")
ap.add_argument("-o", "--out", default="/root/private_ln_stress.icd")
a = ap.parse_args()

NS = "urn:example:private:ns:2025"
LDINST = "LD1"
out = []
w = out.append
q = quoteattr

# Private class names: Z + 3 letters, e.g. ZAAA, ZAAB ...
classes = ["Z" + "".join(c) for c in itertools.islice(itertools.product(string.ascii_uppercase, repeat=3), a.classes)]

# DO kinds cycle: (suffix, DOType id, CDC, FCDA fc, daName)
KINDS = [
    ("Sp", "SPS_P", "SPS", "ST", "stVal"),
    ("In", "INS_P", "INS", "ST", "stVal"),
    ("Mv", "MV_P", "MV", "MX", "mag.f"),
    ("En", "ENS_P", "ENS", "ST", "stVal"),
]


def priv_do(i):
    k = KINDS[i % 4]
    return f"{k[0]}{i + 1:03d}", k


# Standard DOs present in every private LN type
STD_DO = [("Beh", "ENS_Beh", "ST", "stVal"), ("Health", "ENS_Health", "ST", "stVal"),
          ("Mod", "ENC_Mod", "ST", "stVal"), ("NamPlt", "LPL_1", None, None)]

n_priv = max(0, a.dos - len(STD_DO))


def ln_type(cls):
    return f"T_{cls}"


# ---------- datasets ----------
datasets = []  # (name, [fcda strings])


def fcda(lnclass, inst, do, fc, da, prefix=""):
    p = f' prefix="{prefix}"' if prefix else ""
    li = f' lnInst="{inst}"' if inst != "" else ""
    return (f'<FCDA ldInst="{LDINST}"{p} lnClass="{lnclass}"{li} '
            f'fc="{fc}" doName="{do}" daName="{da}" />')


def chunk(name, items):
    for n, i in enumerate(range(0, len(items), a.ds_members), 1):
        datasets.append((f"{name}{n:02d}" if len(items) > a.ds_members else name, items[i:i + a.ds_members]))


# standard dataset (standard LN + standard DOs only)
std_items = [fcda("LLN0", "", "Beh", "ST", "stVal"), fcda("LLN0", "", "Health", "ST", "stVal"),
             fcda("LPHD", "1", "PhyHealth", "ST", "stVal")]
for i in range(1, a.std_mmxu + 1):
    std_items += [fcda("MMXU", i, "TotW", "MX", "mag.f"), fcda("MMXU", i, "Hz", "MX", "mag.f")]
chunk("DS_STD", std_items)

# one dataset per private class: a handful of DOs from each instance
per_inst = max(1, a.ds_members // max(1, a.insts))
for cls in classes:
    items = []
    for inst in range(1, a.insts + 1):
        items.append(fcda(cls, inst, "Beh", "ST", "stVal"))          # private LN + standard DO
        for j in range(min(per_inst - 1, n_priv)):                    # private LN + private DO
            n, k = priv_do(j)
            items.append(fcda(cls, inst, n, k[3], k[4]))
    chunk(f"DS_{cls}", items)

# standard LN + private DOs
mm_items = []
for i in range(1, a.std_mmxu + 1):
    for j in range(min(a.std_priv_dos, per_inst)):
        n, k = priv_do(j)
        mm_items.append(fcda("MMXU", i, "X" + n, k[3], k[4]))
chunk("DS_STDLN_PRIVDO", mm_items)

# mixed dataset: all four member types (cRp19/cBr19)
mixed = [fcda("MMXU", 1, "TotW", "MX", "mag.f"),
         fcda("MMXU", 1, "XSp001", "ST", "stVal"),
         fcda("MMXU", 1, "XIn002", "ST", "stVal"),
         fcda(classes[0], 1, "Beh", "ST", "stVal"),
         fcda(classes[0], 1, "Mod", "ST", "stVal"),
         fcda(classes[0], 1, "Sp005" if n_priv > 4 else "Beh", "ST", "stVal"),
         fcda(classes[-1], a.insts, "Mv003" if n_priv > 2 else "Beh", "MX", "mag.f"),
         fcda("LLN0", "", "Beh", "ST", "stVal")]
datasets.append(("DS_MIXED", mixed))

# ---------- document ----------
w('<?xml version="1.0" encoding="UTF-8"?>')
w('<SCL xmlns="http://www.iec.ch/61850/2003/SCL" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
  'xmlns:ext="urn:example:private:ext" xsi:schemaLocation="http://www.iec.ch/61850/2003/SCL SCL.xsd" '
  'version="2007" revision="B" release="4">')
w('  <Header id="PrivateLNStress" version="1" revision="1" toolID="gen_private_scl.py" nameStructure="IEDName" />')
w('  <Communication>')
w('    <SubNetwork name="subnetwork1" type="8-MMS">')
w('      <ConnectedAP iedName="PVTIED" apName="AP1">')
w('        <Address>')
for t, v in (("IP", "10.0.0.3"), ("IP-SUBNET", "255.255.255.0"), ("IP-GATEWAY", "10.0.0.101"),
             ("OSI-TSEL", "0001"), ("OSI-PSEL", "00000001"), ("OSI-SSEL", "0001")):
    w(f'          <P type="{t}">{v}</P>')
w('        </Address>')
w('      </ConnectedAP>')
w('    </SubNetwork>')
w('  </Communication>')

n_rcb = len(datasets) * 2
w('  <IED name="PVTIED" originalSclVersion="2007" originalSclRevision="B" originalSclRelease="4">')
w('    <Services nameLength="64">')
w('      <DynAssociation />')
w(f'      <ConfDataSet max="{len(datasets) + 20}" maxAttributes="{a.ds_members + 10}" modify="false" />')
w(f'      <ReportSettings cbName="Fix" datSet="Fix" rptID="Fix" optFields="Fix" bufTime="Fix" trgOps="Fix" intgPd="Fix" />')
w(f'      <ConfReportControl max="{n_rcb + 10}" bufMode="both" bufConf="false" />')
w('    </Services>')
w('    <AccessPoint name="AP1">')
w('      <Server>')
w('        <Authentication />')
w(f'        <LDevice inst="{LDINST}">')

# LN0
w('          <LN0 lnClass="LLN0" lnType="T_LLN0" inst="">')
for name, items in datasets:
    w(f'            <DataSet name="{name}">')
    for f in items:
        w(f'              {f}')
    w('            </DataSet>')
for name, items in datasets:
    for buffered in (False, True):
        rn = ("brcb_" if buffered else "urcb_") + name[3:].lower()
        rn = rn[:30]
        extra = ' bufTime="100"' if buffered else ""
        w(f'            <ReportControl name="{rn}" datSet="{name}" rptID="{LDINST}/LLN0.{rn}" '
          f'confRev="1" buffered="{str(buffered).lower()}" intgPd="10000"{extra}>')
        w('              <TrgOps dchg="true" qchg="true" dupd="false" period="true" gi="true" />')
        w('              <OptFields seqNum="true" timeStamp="true" dataSet="true" reasonCode="true" '
          'dataRef="true" entryID="true" configRef="true" bufOvfl="true" />')
        w('              <RptEnabled max="2" />')
        w('            </ReportControl>')
w('            <DOI name="Mod"><DAI name="ctlModel"><Val>status-only</Val></DAI></DOI>')
w('          </LN0>')

# LPHD
w('          <LN lnClass="LPHD" lnType="T_LPHD" inst="1" prefix="" />')

# standard MMXU with private DOs
for i in range(1, a.std_mmxu + 1):
    w(f'          <LN lnClass="MMXU" lnType="T_MMXU" inst="{i}" prefix="">')
    w('            <DOI name="Beh"><DAI name="stVal"><Val>on</Val></DAI></DOI>')
    w('          </LN>')

# private LNs
for cls in classes:
    for inst in range(1, a.insts + 1):
        w(f'          <LN lnClass="{cls}" lnType="{ln_type(cls)}" inst="{inst}" prefix="">')
        w(f'            <Private type="example-private-ln">{cls}/{inst}</Private>')
        w(f'            <DOI name="NamPlt"><DAI name="lnNs"><Val>{NS}</Val></DAI></DOI>')
        w('            <DOI name="Beh"><DAI name="stVal"><Val>on</Val></DAI></DOI>')
        w('          </LN>')

w('        </LDevice>')
w('      </Server>')
w('    </AccessPoint>')
w('  </IED>')

# ---------- DataTypeTemplates ----------
w('  <DataTypeTemplates>')


def lnt(id_, cls, dos):
    w(f'    <LNodeType id="{id_}" lnClass="{cls}">')
    for n, t in dos:
        w(f'      <DO name="{n}" type="{t}" />')
    w('    </LNodeType>')


lnt("T_LLN0", "LLN0", [("Mod", "ENC_Mod"), ("Beh", "ENS_Beh"), ("Health", "ENS_Health"), ("NamPlt", "LPL_1")])
lnt("T_LPHD", "LPHD", [("PhyNam", "DPL_1"), ("PhyHealth", "ENS_Health"), ("Proxy", "SPS_P")])
lnt("T_MMXU", "MMXU", [("Mod", "ENC_Mod"), ("Beh", "ENS_Beh"), ("Health", "ENS_Health"), ("NamPlt", "LPL_1"),
                        ("TotW", "MV_P"), ("Hz", "MV_P")] +
    [("X" + priv_do(i)[0], priv_do(i)[1][1]) for i in range(a.std_priv_dos)])
for cls in classes:
    lnt(ln_type(cls), cls, [("Mod", "ENC_Mod"), ("Beh", "ENS_Beh"), ("Health", "ENS_Health"), ("NamPlt", "LPL_1")] +
        [(priv_do(i)[0], priv_do(i)[1][1]) for i in range(n_priv)])

w('    <DOType id="LPL_1" cdc="LPL">')
w('      <DA name="vendor" bType="VisString255" fc="DC" />')
w('      <DA name="swRev" bType="VisString255" fc="DC" />')
w('      <DA name="d" bType="VisString255" fc="DC" />')
w('      <DA name="lnNs" bType="VisString255" fc="EX" />')
w('    </DOType>')
w('    <DOType id="DPL_1" cdc="DPL">')
w('      <DA name="vendor" bType="VisString255" fc="DC" />')
w('      <DA name="hwRev" bType="VisString255" fc="DC" />')
w('    </DOType>')
for id_, cdc, enum in (("ENS_Beh", "ENS", "BehaviourModeKind"), ("ENS_Health", "ENS", "HealthKind"),
                       ("ENS_P", "ENS", "PrivStateKind")):
    w(f'    <DOType id="{id_}" cdc="{cdc}">')
    w(f'      <DA name="stVal" bType="Enum" type="{enum}" fc="ST" dchg="true" />')
    w('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
    w('      <DA name="t" bType="Timestamp" fc="ST" />')
    w('    </DOType>')
w('    <DOType id="ENC_Mod" cdc="ENC">')
w('      <DA name="stVal" bType="Enum" type="BehaviourModeKind" fc="ST" dchg="true" />')
w('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
w('      <DA name="t" bType="Timestamp" fc="ST" />')
w('      <DA name="ctlModel" bType="Enum" type="CtlModelKind" fc="CF" dchg="true" />')
w('    </DOType>')
w('    <DOType id="SPS_P" cdc="SPS">')
w('      <DA name="stVal" bType="BOOLEAN" fc="ST" dchg="true" />')
w('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
w('      <DA name="t" bType="Timestamp" fc="ST" />')
w('    </DOType>')
w('    <DOType id="INS_P" cdc="INS">')
w('      <DA name="stVal" bType="INT32" fc="ST" dchg="true" />')
w('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
w('      <DA name="t" bType="Timestamp" fc="ST" />')
w('    </DOType>')
w('    <DOType id="MV_P" cdc="MV">')
w('      <DA name="mag" bType="Struct" type="AnalogueValue_P" fc="MX" dchg="true" />')
w('      <DA name="q" bType="Quality" fc="MX" qchg="true" />')
w('      <DA name="t" bType="Timestamp" fc="MX" />')
w('    </DOType>')
w('    <DAType id="AnalogueValue_P">')
w('      <BDA name="f" bType="FLOAT32" />')
w('    </DAType>')
w('    <EnumType id="BehaviourModeKind">')
for o, n in enumerate(["on", "blocked", "test", "test/blocked", "off"], 1):
    w(f'      <EnumVal ord="{o}">{n}</EnumVal>')
w('    </EnumType>')
w('    <EnumType id="HealthKind">')
for o, n in ((1, "Ok"), (2, "Warning"), (3, "Alarm")):
    w(f'      <EnumVal ord="{o}">{n}</EnumVal>')
w('    </EnumType>')
w('    <EnumType id="CtlModelKind">')
for o, n in enumerate(["status-only", "direct-with-normal-security", "sbo-with-normal-security",
                       "direct-with-enhanced-security", "sbo-with-enhanced-security"]):
    w(f'      <EnumVal ord="{o}">{n}</EnumVal>')
w('    </EnumType>')
w('    <EnumType id="PrivStateKind">')
for o, n in enumerate(["idle", "running", "fault", "unknown"]):
    w(f'      <EnumVal ord="{o}">{n}</EnumVal>')
w('    </EnumType>')
w('  </DataTypeTemplates>')
w('</SCL>')

with open(a.out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")

print(f"wrote {a.out}: {len(classes) * a.insts} private LNs ({len(classes)} classes x {a.insts}), "
      f"{n_priv + len(STD_DO)} DOs each, {a.std_mmxu} MMXU x {a.std_priv_dos} private DOs, "
      f"{len(datasets)} datasets, {n_rcb} RCBs")
