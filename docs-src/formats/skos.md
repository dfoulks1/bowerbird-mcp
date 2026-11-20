# SKOS

<!-- seal-banner: Written with Claude Opus 5.5 and Claude Sonnet 5.5. Every command and output on this page was run for real; long lines are shortened. -->

**Use it when** you keep a controlled vocabulary: a glossary, a taxonomy, a thesaurus. SKOS is the W3C standard for
that, written as RDF (Turtle, RDF/XML, JSON-LD, N-Triples or N3).

```text
glossary/
  bower.yaml             format: skos
  glossary.ttl
```

```turtle
@prefix : <http://example.org/glossary/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct: <http://purl.org/dc/terms/> .

:scheme a skos:ConceptScheme ; dct:title "Infrastructure glossary" .

:service a skos:Concept ; skos:prefLabel "Service"@en ;
  skos:definition "A long-running process other systems depend on."@en ;
  skos:narrower :queue .

:queue a skos:Concept ; skos:prefLabel "Queue"@en ; skos:altLabel "message queue"@en ;
  skos:definition "A buffer that decouples a producer from a consumer."@en ;
  skos:broader :service .
```

Each `skos:Concept` is one passage. Its heading is the broader chain, and its text holds the labels, notes and
neighbouring concepts, so a search for the alternate label finds it:

```text
file: glossary.ttl, line: 11, heading: Infrastructure glossary > Service > Queue, type: skos, tier: unverified
text: Also: message queue / Definition: A buffer that decouples a producer from a consumer. / Broader: Service
```

SKOS needs the `rdflib` library. With `uvx`, ask for the extra in the client config: `"--from", "bowerbird-mcp[skos]>=2,<3"`
(the `.mcp.json` that `create` writes does not include it yet). A SKOS file is sealed as a whole, not per concept, and
links between concepts do not count towards ranking.
