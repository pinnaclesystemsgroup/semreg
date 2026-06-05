import sys, os, argparse
from datetime import date
from lxml import etree
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF, DCTERMS, XSD
from pyshacl import validate

CMAP_NS  = 'http://cmap.ihmc.us/xml/cmap/'
DC_NS    = 'http://purl.org/dc/elements/1.1/'
SCHEMA   = Namespace('https://schema.org/')
SEMREG   = Namespace(
    'https://w3id.org/aggateway/semreg/databom-stewardship_')
SCHEME_IRI = URIRef(
    'https://w3id.org/aggateway/semreg/databom-stewardship/')
CREATOR_IRI = URIRef(
    'https://www.pinnaclesystemsgroup.com/people/isaac-riley')
PUBLISHER_IRI = URIRef('https://www.aggateway.org')

SKOS_MAP = {
    'is a type of'     : SKOS.broader,
    'is narrower than' : SKOS.broader,
    'is broader than'  : SKOS.narrower,
    'is attested by'   : SKOS.narrower,
    'consists of'      : SKOS.narrower,
    'is related to'    : SKOS.related,
    'is equivalent to' : SKOS.exactMatch,
}

def cxl_to_graph(cxl_path, id_start=6001):
    tree = etree.parse(cxl_path)
    root = tree.getroot()
    ns  = {'c':  CMAP_NS, 'dc': DC_NS}

    # ── Extract res-meta ─────────────────────────
    title = root.findtext('.//dc:title', namespaces=ns,
        default='DataBOM Stewardship Metadata')
    description = root.findtext('.//dc:description',
        namespaces=ns, default='')
    today = str(date.today())

    # ── Concepts, phrases, connections ───────────
    concepts = {c.get('id'): {
        'label': c.get('label'),
        'defn':  c.get('long-comment', '')}
        for c in root.findall('.//c:concept', ns)}
    phrases = {p.get('id'): p.get('label')
        for p in root.findall('.//c:linking-phrase', ns)}
    conns = root.findall('.//c:connection', ns)

    conn_from = {}
    conn_to   = {}
    for c in conns:
        fid, tid = c.get('from-id'), c.get('to-id')
        conn_from.setdefault(fid, []).append(tid)
        conn_to.setdefault(tid, []).append(fid)

    concept_ids = {v['label']: id_start + i
        for i, v in enumerate(concepts.values())}

    # ── Build graph ───────────────────────────────
    g = Graph()
    g.bind('semreg',  SEMREG)
    g.bind('skos',    SKOS)
    g.bind('dcterms', DCTERMS)
    g.bind('schema',  SCHEMA)

    # Person and Organization declarations
    g.add((CREATOR_IRI,   RDF.type,    SCHEMA.Person))
    g.add((CREATOR_IRI,   SCHEMA.name, Literal('P. Isaac Riley')))
    g.add((CREATOR_IRI,   SCHEMA.url,
           Literal('https://www.pinnaclesystemsgroup.com',
                   datatype=XSD.anyURI)))
    g.add((PUBLISHER_IRI, RDF.type,    SCHEMA.Organization))
    g.add((PUBLISHER_IRI, SCHEMA.name, Literal('AgGateway')))
    g.add((PUBLISHER_IRI, SCHEMA.url,
           Literal('https://www.aggateway.org',
                   datatype=XSD.anyURI)))

    # ConceptScheme
    g.add((SCHEME_IRI, RDF.type,         SKOS.ConceptScheme))
    g.add((SCHEME_IRI, SKOS.prefLabel,
           Literal(title, lang='en')))
    g.add((SCHEME_IRI, SKOS.definition,
           Literal(description or title, lang='en')))
    g.add((SCHEME_IRI, DCTERMS.created,
           Literal(today, datatype=XSD.date)))
    g.add((SCHEME_IRI, DCTERMS.modified,
           Literal(today, datatype=XSD.date)))
    g.add((SCHEME_IRI, DCTERMS.creator,   CREATOR_IRI))
    g.add((SCHEME_IRI, DCTERMS.publisher, PUBLISHER_IRI))
    g.add((SCHEME_IRI, SKOS.historyNote,
           Literal(f'Created {today} by WG35 from CmapTools session.',
                   lang='en')))

    # Identify root concepts (no broader link)
    child_labels = set()
    for phrase_id, phrase_label in phrases.items():
        skos_pred = SKOS_MAP.get(phrase_label.lower(), None)
        if skos_pred == SKOS.broader:
            for sid in conn_to.get(phrase_id, []):
                if sid in concepts:
                    child_labels.add(concepts[sid]['label'])

    # Concepts
    for cid, cdata in concepts.items():
        label = cdata['label']
        defn  = cdata['defn']
        int_id = concept_ids[label]
        iri = SEMREG[f'{int_id:07d}']
        g.add((iri, RDF.type,       SKOS.Concept))
        g.add((iri, SKOS.prefLabel, Literal(label, lang='en')))
        g.add((iri, SKOS.inScheme,  SCHEME_IRI))
        g.add((iri, SKOS.definition,
               Literal(defn if defn else
                       f'{label} — definition pending.',
                       lang='en')))
        if label not in child_labels:
            g.add((iri, SKOS.topConceptOf, SCHEME_IRI))
            g.add((SCHEME_IRI, SKOS.hasTopConcept, iri))

    # Relationships from linking phrases
    for phrase_id, phrase_label in phrases.items():
        skos_pred = SKOS_MAP.get(
            phrase_label.lower(), SKOS.related)
        subjects = conn_to.get(phrase_id, [])
        objects  = conn_from.get(phrase_id, [])
        for sid in subjects:
            for oid in objects:
                if sid in concepts and oid in concepts:
                    s_iri = SEMREG[f'{concept_ids[concepts[sid]["label"]]:07d}']
                    o_iri = SEMREG[f'{concept_ids[concepts[oid]["label"]]:07d}']
                    g.add((s_iri, skos_pred, o_iri))

    return g

parser = argparse.ArgumentParser(
    description='Convert CmapTools CXL to SKOS Turtle')
parser.add_argument('cxl',    help='Input CXL file')
parser.add_argument('output', help='Output Turtle file')
parser.add_argument('--shacl', default=None,
    help='Local SHACL profile .ttl file')
parser.add_argument('--id-start', type=int, default=6001)
args = parser.parse_args()

if not os.path.exists(args.cxl):
    print(f"ERROR: not found: {args.cxl}")
    sys.exit(1)

print(f"Parsing: {args.cxl}")
g = cxl_to_graph(args.cxl, id_start=args.id_start)
print(f"Graph built: {len(g)} triples")

if args.shacl and os.path.exists(args.shacl):
    print(f"Validating against: {args.shacl}")
    conforms, _, results_text = validate(
        g,
        shacl_graph=args.shacl,
        shacl_graph_format='turtle',
        inference='rdfs'
    )
    violations = results_text.count('Severity: sh:Violation')
    warnings   = results_text.count('Severity: sh:Warning')
    print(f"Conforms: {conforms}")
    print(f"Violations: {violations}  Warnings: {warnings}")
    if not conforms:
        print(results_text)
else:
    print("Skipping validation.")

os.makedirs(os.path.dirname(
    os.path.abspath(args.output)), exist_ok=True)
g.serialize(args.output, format='turtle')
print(f"Written to: {args.output}")
