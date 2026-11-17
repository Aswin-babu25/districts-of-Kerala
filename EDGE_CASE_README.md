# Edge-case naming test files

These files target IEC 61850-6 SCL 2007B4 schema name-length limits and the
object-reference-length behaviour discussed with the client:

- `edge_case_naming_valid.icd` — every name field sits AT its documented
  maximum: LDevice inst 64, LN prefix 11, lnInst 12 digits, private DO name
  12, sub-attribute (BDA) name 60, ReportControl/dataset name 32. This file
  should pass XSD schema validation.
- `edge_case_naming_invalid.icd` — the same fields, each pushed ONE character
  over its limit. Each individual field should be rejected by schema
  validation; use it to confirm your tool reports each violation distinctly
  (not just the first one found).
- `check_resolved_names.py` — computes the resolved MMS object reference
  (`LDName/LNName$FC$DataName$DataAttrName`) for every FCDA and RCB and flags
  ones exceeding the combined reference-length limit (commonly cited as 129
  chars, IEC 61850-7-2 clause 22.2 / Tissue 141), even when every individual
  attribute is schema-valid. Run:

      python3 check_resolved_names.py edge_case_naming_valid.icd

  On the current valid file this reports 2 of 6 references as TOO LONG even
  though the file is schema-valid per-field — demonstrating that schema
  validity does not guarantee protocol-level naming conformance.

`gen_edge_case_naming.py` regenerates both ICDs; edit the boundary constants
at the top to try other limits/editions.
