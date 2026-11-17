#!/usr/bin/env python3
"""Generate SCL edge-case naming ICDs: one VALID file where every name sits at
its documented maximum length (IEC 61850-6 SCL 2007B4 schema + 7-2 clause 22.2),
and one INVALID file where each of those same names is pushed one character
over its limit, for negative schema-validation testing.

Boundaries used (see SCL_BaseSimpleTypes.xsd / IEC 61850-7-2 22.2):
  tLDName      <= 64   (LDevice inst)
  tPrefix      <= 11   (LN prefix)
  tLNInst       1..12 digits (LN inst)
  tDataName    <= 12   (DO name, must start upper-case)
  tSubDataName <= 60   (BDA / sub-attribute name, must start lower-case)
  tCBName      <= 32   (ReportControl / dataset name)
  tDataSetName <= 32

Usage: python3 gen_edge_case_naming.py [-o-valid valid.icd] [-o-invalid invalid.icd]
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--o-valid", default="edge_case_naming_valid.icd")
ap.add_argument("--o-invalid", default="edge_case_naming_invalid.icd")
a = ap.parse_args()

NS = "urn:example:private:ns:2025"

# ---- boundary values (valid = exactly at max, invalid = one over) ----
LD_VALID = "L" + "D" * 62 + "X"        # 64 chars, starts with letter
LD_INVALID = LD_VALID + "Z"            # 65 chars -> invalid

PREFIX_VALID = "PfxMaxLen11"           # 11 chars
PREFIX_INVALID = PREFIX_VALID + "X"    # 12 chars -> invalid

LNINST_VALID = "123456789012"          # 12 digits
LNINST_INVALID = "1234567890123"       # 13 digits -> invalid

DONAME_VALID = "PrivDoMax12"           # 11 chars... need exactly 12
DONAME_VALID = "PrivDoMax1X"           # ensure len 11? recompute below
DONAME_VALID = ("PrivD" + "oMax12")    # build precisely
DONAME_VALID = "PrivDoNam12"           # check length below, adjust programmatically


def fit(s, n, pad="X"):
    s = s[:n]
    while len(s) < n:
        s += pad
    return s


DONAME_VALID = fit("PrivDoNam", 12)        # 12 chars, starts uppercase (tDataName)
DONAME_INVALID = DONAME_VALID + "Y"        # 13 chars -> invalid

SUBDA_VALID = fit("subAttrNameAtTheDocumentedSixtyCharacterMaximumBoundaryXX", 60)  # 60 chars, lowercase start
SUBDA_INVALID = SUBDA_VALID + "z"          # 61 chars -> invalid

CBNAME_VALID = fit("rcbNameAtMax32CharsBoundaryXXXX", 32)   # 32 chars
CBNAME_INVALID = CBNAME_VALID + "Q"                          # 33 -> invalid

DSNAME_VALID = fit("datasetNameAtMax32CharsBoundary", 32)
DSNAME_INVALID = DSNAME_VALID + "Q"

for name, val in [("LD_VALID", LD_VALID), ("PREFIX_VALID", PREFIX_VALID), ("LNINST_VALID", LNINST_VALID),
                  ("DONAME_VALID", DONAME_VALID), ("SUBDA_VALID", SUBDA_VALID),
                  ("CBNAME_VALID", CBNAME_VALID), ("DSNAME_VALID", DSNAME_VALID)]:
    pass  # length assertions below

assert len(LD_VALID) == 64, len(LD_VALID)
assert len(PREFIX_VALID) == 11, len(PREFIX_VALID)
assert len(LNINST_VALID) == 12, len(LNINST_VALID)
assert len(DONAME_VALID) == 12, len(DONAME_VALID)
assert len(SUBDA_VALID) == 60, len(SUBDA_VALID)
assert len(CBNAME_VALID) == 32, len(CBNAME_VALID)
assert len(DSNAME_VALID) == 32, len(DSNAME_VALID)


def build(out_path, ld, prefix, lninst, doname, subda, cbname, dsname, tag):
    w = []
    a_ = w.append
    a_('<?xml version="1.0" encoding="UTF-8"?>')
    a_('<SCL xmlns="http://www.iec.ch/61850/2003/SCL" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
       'xsi:schemaLocation="http://www.iec.ch/61850/2003/SCL SCL.xsd" version="2007" revision="B" release="4">')
    a_(f'  <Header id="EdgeCaseNaming_{tag}" version="1" revision="1" toolID="gen_edge_case_naming.py" nameStructure="IEDName" />')
    a_('  <Communication>')
    a_('    <SubNetwork name="subnetwork1" type="8-MMS">')
    a_('      <ConnectedAP iedName="PVTIED" apName="AP1">')
    a_('        <Address>')
    for t, v in (("IP", "10.0.0.3"), ("IP-SUBNET", "255.255.255.0"), ("IP-GATEWAY", "10.0.0.101"),
                 ("OSI-TSEL", "0001"), ("OSI-PSEL", "00000001"), ("OSI-SSEL", "0001")):
        a_(f'          <P type="{t}">{v}</P>')
    a_('        </Address>')
    a_('      </ConnectedAP>')
    a_('    </SubNetwork>')
    a_('  </Communication>')
    a_('  <IED name="PVTIED" originalSclVersion="2007" originalSclRevision="B" originalSclRelease="4">')
    a_('    <Services nameLength="64">')
    a_('      <DynAssociation />')
    a_('      <ConfDataSet max="5" maxAttributes="20" modify="false" />')
    a_('      <ReportSettings cbName="Fix" datSet="Fix" rptID="Fix" optFields="Fix" bufTime="Fix" trgOps="Fix" intgPd="Fix" />')
    a_('      <ConfReportControl max="5" bufMode="both" bufConf="false" />')
    a_('    </Services>')
    a_('    <AccessPoint name="AP1">')
    a_('      <Server>')
    a_('        <Authentication />')
    a_(f'        <LDevice inst="{ld}">')
    a_('          <LN0 lnClass="LLN0" lnType="T_LLN0" inst="">')
    a_(f'            <DataSet name="{dsname}">')
    a_(f'              <FCDA ldInst="{ld}" lnClass="ZABC" prefix="{prefix}" lnInst="{lninst}" fc="ST" doName="Beh" daName="stVal" />')
    a_(f'              <FCDA ldInst="{ld}" lnClass="ZABC" prefix="{prefix}" lnInst="{lninst}" fc="ST" doName="{doname}" daName="stVal" />')
    a_(f'              <FCDA ldInst="{ld}" lnClass="MMXU" lnInst="1" fc="MX" doName="{doname}" daName="mag.{subda}" />')
    a_('            </DataSet>')
    a_(f'            <ReportControl name="{cbname}" datSet="{dsname}" rptID="{ld}/LLN0.{cbname}" confRev="1" '
       f'buffered="true" intgPd="10000" bufTime="100">')
    a_('              <TrgOps dchg="true" qchg="true" dupd="false" period="true" gi="true" />')
    a_('              <OptFields seqNum="true" timeStamp="true" dataSet="true" reasonCode="true" '
       'dataRef="true" entryID="true" configRef="true" bufOvfl="true" />')
    a_('              <RptEnabled max="1" />')
    a_('            </ReportControl>')
    a_('            <DOI name="Mod"><DAI name="ctlModel"><Val>status-only</Val></DAI></DOI>')
    a_('          </LN0>')
    a_(f'          <LN lnClass="ZABC" lnType="T_ZABC" inst="{lninst}" prefix="{prefix}">')
    a_(f'            <Private type="example-private-ln">edge-case {tag}</Private>')
    a_(f'            <DOI name="NamPlt"><DAI name="lnNs"><Val>{NS}</Val></DAI></DOI>')
    a_('            <DOI name="Beh"><DAI name="stVal"><Val>on</Val></DAI></DOI>')
    a_(f'            <DOI name="{doname}"><DAI name="stVal"><Val>true</Val></DAI></DOI>')
    a_('          </LN>')
    a_('          <LN lnClass="MMXU" lnType="T_MMXU" inst="1" prefix="">')
    a_('            <DOI name="Beh"><DAI name="stVal"><Val>on</Val></DAI></DOI>')
    a_(f'            <DOI name="{doname}"><DAI name="mag"><DAI name="{subda}"><Val>0.0</Val></DAI></DAI></DOI>')
    a_('          </LN>')
    a_('        </LDevice>')
    a_('      </Server>')
    a_('    </AccessPoint>')
    a_('  </IED>')

    a_('  <DataTypeTemplates>')
    a_('    <LNodeType id="T_LLN0" lnClass="LLN0">')
    a_('      <DO name="Mod" type="ENC_Mod" />')
    a_('      <DO name="Beh" type="ENS_Beh" />')
    a_('      <DO name="NamPlt" type="LPL_1" />')
    a_('    </LNodeType>')
    a_(f'    <LNodeType id="T_ZABC" lnClass="ZABC">')
    a_('      <DO name="Beh" type="ENS_Beh" />')
    a_('      <DO name="NamPlt" type="LPL_1" />')
    a_(f'      <DO name="{doname}" type="SPS_P" />')
    a_('    </LNodeType>')
    a_('    <LNodeType id="T_MMXU" lnClass="MMXU">')
    a_('      <DO name="Beh" type="ENS_Beh" />')
    a_(f'      <DO name="{doname}" type="MV_SubDA" />')
    a_('    </LNodeType>')
    a_('    <DOType id="LPL_1" cdc="LPL">')
    a_('      <DA name="vendor" bType="VisString255" fc="DC" />')
    a_('      <DA name="lnNs" bType="VisString255" fc="EX" />')
    a_('    </DOType>')
    a_('    <DOType id="ENS_Beh" cdc="ENS">')
    a_('      <DA name="stVal" bType="Enum" type="BehaviourModeKind" fc="ST" dchg="true" />')
    a_('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
    a_('      <DA name="t" bType="Timestamp" fc="ST" />')
    a_('    </DOType>')
    a_('    <DOType id="ENC_Mod" cdc="ENC">')
    a_('      <DA name="stVal" bType="Enum" type="BehaviourModeKind" fc="ST" dchg="true" />')
    a_('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
    a_('      <DA name="t" bType="Timestamp" fc="ST" />')
    a_('      <DA name="ctlModel" bType="Enum" type="CtlModelKind" fc="CF" dchg="true" />')
    a_('    </DOType>')
    a_('    <DOType id="SPS_P" cdc="SPS">')
    a_('      <DA name="stVal" bType="BOOLEAN" fc="ST" dchg="true" />')
    a_('      <DA name="q" bType="Quality" fc="ST" qchg="true" />')
    a_('      <DA name="t" bType="Timestamp" fc="ST" />')
    a_('    </DOType>')
    a_('    <DOType id="MV_SubDA" cdc="MV">')
    a_('      <DA name="mag" bType="Struct" type="AnalogueValue_SubDA" fc="MX" dchg="true" />')
    a_('      <DA name="q" bType="Quality" fc="MX" qchg="true" />')
    a_('      <DA name="t" bType="Timestamp" fc="MX" />')
    a_('    </DOType>')
    a_(f'    <DAType id="AnalogueValue_SubDA">')
    a_(f'      <BDA name="{subda}" bType="FLOAT32" />')
    a_('    </DAType>')
    a_('    <EnumType id="BehaviourModeKind">')
    for o, n in enumerate(["on", "blocked", "test", "test/blocked", "off"], 1):
        a_(f'      <EnumVal ord="{o}">{n}</EnumVal>')
    a_('    </EnumType>')
    a_('    <EnumType id="CtlModelKind">')
    for o, n in enumerate(["status-only", "direct-with-normal-security", "sbo-with-normal-security",
                           "direct-with-enhanced-security", "sbo-with-enhanced-security"]):
        a_(f'      <EnumVal ord="{o}">{n}</EnumVal>')
    a_('    </EnumType>')
    a_('  </DataTypeTemplates>')
    a_('</SCL>')

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")


build(a.o_valid, LD_VALID, PREFIX_VALID, LNINST_VALID, DONAME_VALID, SUBDA_VALID, CBNAME_VALID, DSNAME_VALID, "VALID")
build(a.o_invalid, LD_INVALID, PREFIX_INVALID, LNINST_INVALID, DONAME_INVALID, SUBDA_INVALID, CBNAME_INVALID, DSNAME_INVALID, "INVALID")

print("wrote", a.o_valid, "(all names AT the documented maximum -> should validate OK)")
print("wrote", a.o_invalid, "(every name ONE character OVER its maximum -> each should be rejected)")
print()
print(f"{'field':14s}{'valid len':>10s}{'invalid len':>13s}")
for label, v, i in [("LDevice inst", LD_VALID, LD_INVALID), ("prefix", PREFIX_VALID, PREFIX_INVALID),
                    ("lnInst", LNINST_VALID, LNINST_INVALID), ("DO name", DONAME_VALID, DONAME_INVALID),
                    ("sub-DA name", SUBDA_VALID, SUBDA_INVALID), ("RCB name", CBNAME_VALID, CBNAME_INVALID),
                    ("dataset name", DSNAME_VALID, DSNAME_INVALID)]:
    print(f"{label:14s}{len(v):>10d}{len(i):>13d}")
