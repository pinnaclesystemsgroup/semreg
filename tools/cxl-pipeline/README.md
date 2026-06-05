# CmapTools CXL ↔ SKOS Turtle Pipeline

Bidirectional conversion between CmapTools concept maps
and validated SKOS Turtle for semreg vocabulary submission.

## Forward pipeline (CXL → Turtle)

    python3 cxl_to_turtle.py \
      cmap/sessions/your-session.cxl \
      output.ttl \
      --shacl shacl/vp4cat.ttl

## Reverse pipeline (Turtle → CXL)

    python3 turtle_to_cxl.py \
      vocabularies/databom-stewardship/concept_scheme.ttl \
      cmap/sessions/output.cxl

## Round-trip verified

concept_scheme.ttl → CXL → Turtle: 0 violations

## Requirements

    pip install rdflib pyshacl lxml owlrl

## Validation target

0 violations against vp4cat-5.2 SHACL profile.
5-15 advisory warnings (sh:Warning) — provenance notes,
non-blocking for v0.1 submissions.
