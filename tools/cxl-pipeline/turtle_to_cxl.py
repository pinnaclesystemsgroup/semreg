"""
turtle_to_cxl.py
Converts a validated SKOS Turtle file to CmapTools CXL format.
Reverses the cxl_to_turtle.py pipeline for provenance traceability.
"""
import sys
from rdflib import Graph, Namespace
from rdflib.namespace import SKOS, RDF
from datetime import date

SEMREG = Namespace(
    'https://w3id.org/aggateway/semreg/databom-stewardship_')
SCHEME_IRI = 'https://w3id.org/aggateway/semreg/databom-stewardship/'

def ttl_to_cxl(ttl_path, cxl_path, session_title=None):
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Extract concepts
    concepts = []
    for s in g.subjects(RDF.type, SKOS.Concept):
        local_id = str(s).split('_')[-1]
        label = g.value(s, SKOS.prefLabel)
        defn  = g.value(s, SKOS.definition)
        concepts.append({
            'id':    f'C{local_id}',
            'label': str(label) if label else local_id,
            'defn':  str(defn)  if defn  else ''
        })

    # Extract relationships
    relations = []
    pid = 1
    seen = set()
    for s in g.subjects(RDF.type, SKOS.Concept):
        s_local = str(s).split('_')[-1]
        for broader in g.objects(s, SKOS.broader):
            b_local = str(broader).split('_')[-1]
            key = (s_local, b_local)
            if key not in seen:
                seen.add(key)
                relations.append({
                    'pid':     f'P{pid}',
                    'phrase':  'is a type of',
                    'from_id': f'C{s_local}',
                    'to_id':   f'C{b_local}'
                })
                pid += 1
        for related in g.objects(s, SKOS.related):
            r_local = str(related).split('_')[-1]
            key = tuple(sorted([s_local, r_local]))
            if key not in seen:
                seen.add(key)
                relations.append({
                    'pid':     f'P{pid}',
                    'phrase':  'is related to',
                    'from_id': f'C{s_local}',
                    'to_id':   f'C{r_local}'
                })
                pid += 1

    title = session_title or 'DataBOM Stewardship Metadata'
    today = str(date.today())

    # Build CXL
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<cmap xmlns="http://cmap.ihmc.us/xml/cmap/"',
        '      xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '      xmlns:dcterms="http://purl.org/dc/terms/">',
        '  <res-meta>',
        f'    <dc:title>{title}</dc:title>',
        '    <dc:description>What stewardship metadata attributes '
        'are required for ADAPT data governance?</dc:description>',
        '    <dc:creator>P. Isaac Riley</dc:creator>',
        f'    <dcterms:created>{today}T00:00:00Z</dcterms:created>',
        '  </res-meta>',
        '  <map>',
        '    <concept-list>',
    ]

    for c in concepts:
        defn_attr = f' long-comment="{c["defn"]}"' if c['defn'] else ''
        lines.append(
            f'      <concept id="{c["id"]}" '
            f'label="{c["label"]}"{defn_attr}/>')

    lines.append('    </concept-list>')
    lines.append('    <linking-phrase-list>')
    for r in relations:
        lines.append(
            f'      <linking-phrase id="{r["pid"]}" '
            f'label="{r["phrase"]}"/>')
    lines.append('    </linking-phrase-list>')
    lines.append('    <connection-list>')

    conn_id = 1
    for r in relations:
        lines.append(
            f'      <connection id="L{conn_id}" '
            f'from-id="{r["from_id"]}" to-id="{r["pid"]}"/>')
        conn_id += 1
        lines.append(
            f'      <connection id="L{conn_id}" '
            f'from-id="{r["pid"]}" to-id="{r["to_id"]}"/>')
        conn_id += 1

    lines += [
        '    </connection-list>',
        '  </map>',
        '</cmap>'
    ]

    with open(cxl_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Concepts: {len(concepts)}")
    print(f"Relations: {len(relations)}")
    print(f"Written to: {cxl_path}")

if __name__ == '__main__':
    ttl  = sys.argv[1] if len(sys.argv) > 1 \
        else 'semreg/vocabularies/databom-stewardship/concept_scheme.ttl'
    cxl  = sys.argv[2] if len(sys.argv) > 2 \
        else 'cmap/sessions/databom-from-pr2.cxl'
    ttl_to_cxl(ttl, cxl)
