"""Tag each failed judge item with error types (rule-based, on the judge's evidence text). Writes errors.json."""
import json, re, collections
d = json.load(open("rounds.json"))
RULES = [  # (tag, item regex, evidence regex)
    ("Over-recovers eluate (90-100 uL, not ~80)", r"elution_recovery|fidelity_to_paper", r"(100|95|90) ?uL.*(80|instead)|recover(s|y)? (the full )?(100|95|90)|rather than (about )?~?80|not (about )?~?80"),
    ("Wrong reagent order (sample before beads)", r"binding_and_separation|fidelity_to_paper", r"samples? (is |are )?(added |go(es)? in )?(first|before)|samples? first|reorder|revers"),
    ("Pipette-mixes competent cells (unrequested)", r"fidelity_to_task|dna_addition", r"mix_after|mix\(3|3x ?10|pipette mix"),
    ("Adds unrequested step, pause or delay", r"fidelity_", r"protocol\.pause|extra|unrequested|not in the (paper|task)|does not include|settle|flick"),
    ("Hallucinated paper authors in metadata", r"fidelity_to_paper", r"author|attribut|et al"),
    ("No mix at elution", r"elution_recovery|fidelity_to_paper", r"never mixed|no (elution )?mix|lacks mixing"),
    ("Ethanol not labelled 70%", r"fidelity_to_paper", r"70 ?%"),
]
rows = []
for r in d:
    for f in r["failed_items"]:
        tags = [t for t, ir, er in RULES if re.search(ir, f["item"]) and re.search(er, f["evidence"], re.I)]
        rows.append(dict(round=r["round"][:2], model=r["model"].replace("claude-", ""), task=r["task"], item=f["item"],
                         tags=tags or ["(other / style)"], evidence=f["evidence"]))
json.dump(rows, open("errors.json", "w"), indent=1)
c = collections.Counter()
seen = {(x["round"], x["model"], x["task"], t) for x in rows if x["round"] in ("R3", "R4", "R5", "R6", "R7") for t in x["tags"]}
for (_, m, _, t) in seen: c[(t, m)] += 1
for t in sorted({k[0] for k in c}):
    print(f"{t:46}", {m: c[(t, m)] for m in ("opus-5-5", "sonnet-5-5", "fable-5-1")})
print([ (x['round'],x['model'],x['item'],x['evidence'][:90]) for x in rows if x['tags']==['(other / style)'] and x['round']!='R2'])
