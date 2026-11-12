#!/usr/bin/env python3
"""Generate an IEC 61850 SCL (ICD, Ed2 2007B4) with standard LNs carrying private DOs.

Default: 10 standard LNs, each with 4 standard DOs (Mod, Beh, Health, NamPlt)
plus 40 private DOs. Per-LN datasets (URCB + BRCB each), a standard-only dataset
and a mixed dataset.

Usage: python3 gen_std_ln_private_do.py [--dos 40] [--ds-members 50] [-o out.icd]
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--dos", type=int, default=40, help="private DOs per standard LN")
ap.add_argument("--ds-members", type=int, default=50, help="max FCDAs per dataset")
ap.add_argument("-o", "--out", default="std_ln_private_do.icd")
a = ap.parse_args()

LD = "LD1"
NS = "urn:example:private:ns:2025"
STD_LNS = ["GGIO", "MMXU", "MMTR", "XCBR", "XSWI", "CSWI", "PTOC", "PTRC", "STMP", "MSQI"]

# (name suffix, DOType id, fc, daName)
KINDS = [("Sp", "SPS_P", "ST", "stVal"), ("In", "INS_P", "ST", "stVal"),
         ("Mv", "MV_P", "MX", "mag.f"), ("En", "ENS_P", "ST", "stVal")]


def priv_do(i):
    k = KINDS[i % len(KINDS)]
    return f"Pvt{k[0]}{i + 1:02d}", k


out = []
w = out.append


def fcda(cls, inst, do, fc, da):
    li = f' lnInst="{inst}"' if inst else ""
    return f'<FCDA ldInst="{LD}" lnClass="{cls}"{li} fc="{fc}" doName="{do}" daName="{da}" />'


datasets = []


def add_ds(name, items):
    for n, i in enumerate(range(0, len(items), a.ds_members), 1):
        nm = name if len(items) <= a.ds_members else f"{name}_{n:02d}"
        datasets.append((nm, items[i:i + a.ds_members]))


add_ds("DS_STD", [fcda("LLN0", "", "Beh", "ST", "stVal"), fcda("LPHD", "1", "PhyHealth", "ST", "stVal")] +
       [fcda(c, "1", d, "ST", "stVal") for c in STD_LNS for d in ("Beh", "Health")])
for c in STD_LNS:
    items = [fcda(c, "1", "Beh", "ST", "stVal")]
    for i in range(a.dos):
        n, k = priv_do(i)
        items.append(fcda(c, "1", n, k[2], k[3]))
    add_ds(f"DS_{c}", items)
mixed = [fcda("LLN0", "", "Beh", "ST", "stVal")]
for c in STD_LNS:
    mixed.append(fcda(c, "1", "Health", "ST", "stVal"))
    n, k = priv_do(STD_LNS.index(c) % a.dos)
    mixed.append(fcda(c, "1", n, k[2], k[3]))
add_ds("DS_MIXED", mixed)

w('<?xml version="1.0" encoding="UTF-8"?>')
w('<SCL xmlns="http://www.iec.ch/61850/2003/SCL" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
  'xsi:schemaLocation="http://www.iec.ch/61850/2003/SCL SCL.xsd" version="2007" revision="B" release="4">')
w('  <Header id="StdLnPrivateDo" version="1" revision="1" toolID="gen_std_ln_private_do.py" nameStructure="IEDName" />')
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
w('  <IED name="PVTIED" originalSclVersion="2007" originalSclRevision="B" originalSclRelease="4">')
w('    <Services nameLength="64">')
w('      <DynAssociation />')
w(f'      <ConfDataSet max="{len(datasets) + 10}" maxAttributes="{a.ds_members + 10}" modify="false" />')
w('      <ReportSettings cbName="Fix" datSet="Fix" rptID="Fix" optFields="Fix" bufTime="Fix" trgOps="Fix" intgPd="Fix" />')
w(f'      <ConfReportControl max="{len(datasets) * 2 + 10}" bufMode="both" bufConf="false" />')
w('    </Services>')
w('    <AccessPoint name="AP1">')
w('      <Server>')
w('        <Authentication />')
w(f'        <LDevice inst="{LD}">')
w('          <LN0 lnClass="LLN0" lnType="T_LLN0" inst="">')
for name, items in datasets:
    w(f'            <DataSet name="{name}">')
    for f in items:
        w(f'              {f}')
    w('            </DataSet>')
for name, _ in datasets:
    for buffered in (False, True):
        rn = (("brcb_" if buffered else "urcb_") + name[3:].lower())[:30]
        extra = ' bufTime="100"' if buffered else ""
        w(f'            <ReportControl name="{rn}" datSet="{name}" rptID="{LD}/LLN0.{rn}" confRev="1" '
          f'buffered="{str(buffered).lower()}" intgPd="10000"{extra}>')
        w('              <TrgOps dchg="true" qchg="true" dupd="false" period="true" gi="true" />')
        w('              <OptFields seqNum="true" timeStamp="true" dataSet="true" reasonCode="true" '
          'dataRef="true" entryID="true" configRef="true" bufOvfl="true" />')
        w('              <RptEnabled max="2" />')
        w('            </ReportControl>')
w('            <DOI name="Mod"><DAI name="ctlModel"><Val>status-only</Val></DAI></DOI>')
w('          </LN0>')
w('          <LN lnClass="LPHD" lnType="T_LPHD" inst="1" prefix="" />')
for c in STD_LNS:
    w(f'          <LN lnClass="{c}" lnType="T_{c}" inst="1" prefix="">')
    w('            <DOI name="Beh"><DAI name="stVal"><Val>on</Val></DAI></DOI>')
    w('            <DOI name="Mod"><DAI name="ctlModel"><Val>status-only</Val></DAI></DOI>')
    w(f'            <DOI name="NamPlt"><DAI name="lnNs"><Val>{NS}</Val></DAI></DOI>')
    w('          </LN>')
w('        </LDevice>')
w('      </Server>')
w('    </AccessPoint>')
w('  </IED>')

w('  <DataTypeTemplates>')
COMMON = [("Mod", "ENC_Mod"), ("Beh", "ENS_Beh"), ("Health", "ENS_Health"), ("NamPlt", "LPL_1")]


def lnt(id_, cls, dos):
    w(f'    <LNodeType id="{id_}" lnClass="{cls}">')
    for n, t in dos:
        w(f'      <DO name="{n}" type="{t}" />')
    w('    </LNodeType>')


lnt("T_LLN0", "LLN0", COMMON)
lnt("T_LPHD", "LPHD", [("PhyNam", "DPL_1"), ("PhyHealth", "ENS_Health"), ("Proxy", "SPS_P")])
for c in STD_LNS:
    lnt(f"T_{c}", c, COMMON + [(priv_do(i)[0], priv_do(i)[1][1]) for i in range(a.dos)])

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
for id_, enum in (("ENS_Beh", "BehaviourModeKind"), ("ENS_Health", "HealthKind"), ("ENS_P", "PrivStateKind")):
    w(f'    <DOType id="{id_}" cdc="ENS">')
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
for id_, cdc, bt in (("SPS_P", "SPS", "BOOLEAN"), ("INS_P", "INS", "INT32")):
    w(f'    <DOType id="{id_}" cdc="{cdc}">')
    w(f'      <DA name="stVal" bType="{bt}" fc="ST" dchg="true" />')
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
for eid, vals, start in (("BehaviourModeKind", ["on", "blocked", "test", "test/blocked", "off"], 1),
                         ("HealthKind", ["Ok", "Warning", "Alarm"], 1),
                         ("CtlModelKind", ["status-only", "direct-with-normal-security", "sbo-with-normal-security",
                                           "direct-with-enhanced-security", "sbo-with-enhanced-security"], 0),
                         ("PrivStateKind", ["idle", "running", "fault", "unknown"], 0)):
    w(f'    <EnumType id="{eid}">')
    for o, v in enumerate(vals, start):
        w(f'      <EnumVal ord="{o}">{v}</EnumVal>')
    w('    </EnumType>')
w('  </DataTypeTemplates>')
w('</SCL>')

with open(a.out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print(f"wrote {a.out}: {len(STD_LNS)} standard LNs x ({len(COMMON)} std + {a.dos} private DOs), "
      f"{len(datasets)} datasets, {len(datasets) * 2} RCBs")
