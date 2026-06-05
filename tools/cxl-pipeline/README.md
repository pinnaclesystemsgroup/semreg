# CmapTools CXL to SKOS Turtle Pipeline

Converts CmapTools concept map exports (.cxl) to validated
SKOS Turtle for semreg vocabulary submission.

## Usage

    python3 cxl_to_turtle.py \
      cmap/sessions/your-session.cxl \
      output.ttl \
      --shacl shacl/vp4cat.ttl

## Requirements

    pip install rdflib pyshacl lxml owlrl

## Output

0 violations against vp4cat-5.2 SHACL profile.
5 advisory warnings (sh:Warning) — provenance notes,
non-blocking for v0.1 submissions.
