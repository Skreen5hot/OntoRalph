# Ontological Definition Style Guide & Checklist

**Version**: 3.1  
**Date**: 2026-01-23  
**Purpose**: Ensure all TagTeam ontology definitions are rigorous, non-circular, BFO/CCO-compliant, and philosophically defensible against realist critique.  
**Audience**: Ontology developers, contributors, reviewers, philosophers  
---

## Preamble: Philosophical Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           TAGTEAM'S PHILOSOPHICAL POSITION: REALISM ABOUT                    │
│                    DISCOURSE-DERIVED INFORMATION CONTENT                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TagTeam takes a realist stance toward linguistic information entities.    │
│  We hold that:                                                              │
│                                                                             │
│  1. LINGUISTIC ENTITIES EXIST                                               │
│     Utterances, inscriptions, and their structural components are real     │
│     entities with physical instantiation, causal powers, identity          │
│     conditions, and persistence.                                           │
│                                                                             │
│  2. THEY ARE INFORMATION CONTENT ENTITIES                                   │
│     They are Generically Dependent Continuants (per BFO) concretized in    │
│     bearers but not identical to those bearers.                            │
│                                                                             │
│  3. THEIR ABOUTNESS IS DISCOURSE-MEDIATED                                   │
│     They are about worldly entities AS INTRODUCED IN DISCOURSE—not         │
│     directly about mind-independent reality unmediated by communicative    │
│     context. This is still realism: the mediation is itself real.          │
│                                                                             │
│  4. DISCOURSE MEDIATION IS CAUSALLY CONSTRAINED                             │
│     Discourse introduces candidates for denotation, but admissible         │
│     targets are constrained by causal, historical, or institutional        │
│     relations to the world. Aboutness is not free-floating.                │
│                                                                             │
│  5. DENOTATION IS CONSTRAINED, NOT GUARANTEED                               │
│     Grammatical and semantic features constrain interpretation.            │
│     Successful denotation depends on discourse context, speaker intent,    │
│     and referential success. Denotation may fail in non-referential        │
│     contexts (fiction, hypotheticals, failed reference).                   │
│                                                                             │
│  6. NORMATIVE/MODAL DENOTATA REQUIRE GROUNDING                              │
│     When denoting normative statuses or modal aspects, the denotatum       │
│     must be grounded in socially or institutionally real entities,         │
│     not merely in linguistic or cognitive acts.                            │
│                                                                             │
│  7. THE ALTERNATIVE IS INADEQUATE                                           │
│     A realist ontology that is unable to adequately represent linguistic   │
│     information leaves provenance unrepresentable and severs the link      │
│     between information and world. Language is part of reality.            │
│                                                                             │
│  TagTeam's Tier 1 classes are therefore legitimate subclasses of           │
│  cco:InformationContentEntity. They represent the informational            │
│  structures through which we access knowledge of worldly entities          │
│  (Tier 2). This guide ensures definitions meet the standards required      │
│  to defend this position.                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part I: Foundational Principles

### 1.1 The Aristotelian Pattern

Every definition follows the **genus-differentia** pattern:

```
An X is a [GENUS] that [DIFFERENTIA]
```

| Component | What It Does | Example |
|-----------|--------------|---------|
| **Genus** | Names the immediate parent class | "An information content entity…" |
| **Differentia** | Distinguishes from siblings by essential properties | "…that is about an occurrent as introduced in discourse and denotes its temporal and modal boundaries" |

The genus places the definiendum in its proper category. The differentia specifies what makes it different from other members of that category.

**The "So What?" Rule**: If the differentia could apply to the parent class without losing meaning, the definition is too broad. Test by substituting—if "An ICE that is about something" works equally well for your class and its siblings, your differentia has failed.

**Fallibilism Note**: In domains where essences are still under investigation, definitions may initially capture necessary but not yet sufficient conditions, provided this is explicitly noted. This reflects the fallibilism inherent in any scientific ontology—we may refine our understanding over time without this constituting a defect in the current formulation.

### 1.2 The Aboutness Requirement (for ICEs)

Information Content Entities in BFO/CCO are defined by what they **denote**—the portion of reality they are about. Every ICE definition must answer:

> "What portion of reality does this entity denote?"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THE ABOUTNESS TEST                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ASK: "This information content entity denotes ___________."               │
│                                                                             │
│  GOOD ANSWERS:                                                              │
│    • "...an occurrent (event, process, or state) as introduced in         │
│        discourse"                                                          │
│    • "...a continuant (person, object, quality) as referred to in         │
│        discourse"                                                          │
│    • "...the normative status of an act as grounded in institutional      │
│        reality"                                                            │
│    • "...a relation between two particulars"                               │
│    • "...a quality inhering in a continuant"                               │
│                                                                             │
│  BAD ANSWERS:                                                               │
│    • "...a verb phrase" (this is the entity itself, not what it denotes)  │
│    • "...text" (text is the bearer, not what it denotes)                  │
│    • "...linguistic structure" (structure ≠ referent)                      │
│    • "...data" (data is concretization, not denotation)                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Terminological Requirements**:

| Prefer | Avoid | Reason |
|--------|-------|--------|
| "denotes" | "represents" | "Denotes" keeps focus on ICE-to-world relationship |
| "is about" | "encodes" | "Encodes" implies manner of expression (linguistic layer) |

**The Discourse-Mediation Qualifier**:

For Tier 1 (discourse-derived) ICEs, aboutness is mediated by discourse context. Include the phrase **"as introduced in discourse"** or equivalent to acknowledge this:

| Without Qualifier (Risky) | With Qualifier (Defensible) |
|---------------------------|----------------------------|
| "An ICE that is about an occurrent" | "An ICE that is about an occurrent **as introduced in discourse**" |

This qualifier:
- Acknowledges that aboutness is mediated, not direct
- Prevents naive referentialism (parsing ≠ ontological discovery)
- Remains realist (discourse introduction is itself a real event)
- Enables Tier 1/Tier 2 separation

**The Causal-Historical Constraint** (NEW in v3.1):

Discourse mediation is not unlimited. Admissible targets of denotation are constrained:

> **Discourse introduces candidates for denotation, but the admissible targets of denotation are constrained by causal, historical, or institutional relations to the world.**

This principle:
- Preserves space for fiction, error, and hypothesis
- Blocks free-floating "aboutness" determined by discourse alone
- Ensures that even failed reference involves a causal-historical connection (the speaker's causal contact with the world that prompted the attempt)
- Distinguishes real mediation from pure semantic construction

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE CAUSAL-HISTORICAL CONSTRAINT                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  WITHOUT THIS CONSTRAINT:                                                   │
│  ─────────────────────────                                                  │
│  • Fictional dragons and real treatments become ontologically symmetric    │
│  • Discourse alone determines aboutness                                    │
│  • Risk of collapsing into semantic constructivism                         │
│                                                                             │
│  WITH THIS CONSTRAINT:                                                      │
│  ──────────────────────                                                     │
│  • Fiction is accommodated (author has causal contact with world that      │
│    prompts imaginative combination)                                        │
│  • Error is accommodated (failed reference involves real causal attempt)   │
│  • Hypothesis is accommodated (constrained by institutional practices      │
│    of science, law, etc.)                                                  │
│  • Pure semantic construction is blocked                                   │
│                                                                             │
│  THE KEY INSIGHT:                                                           │
│  ────────────────                                                           │
│  Even when denotation fails, the discourse act is causally and             │
│  historically embedded in reality. The mediation is real even when the     │
│  reference is not.                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Grounding Requirement for Normative/Modal Denotata**:

When denoting normative, modal, or discourse-related aspects, the denotatum must be grounded in socially or institutionally real entities, not merely in linguistic or cognitive acts.

| Ungrounded (Problematic) | Grounded (Acceptable) |
|--------------------------|-----------------------|
| "denotes the normative status" | "denotes the normative status as grounded in institutional rules" |
| "denotes presentation in discourse" | "denotes the mode under which the occurrent is presented, constrained by discourse context" |

**Gold Standard ICE Formula**:

```
An ICE that is about some [BFO ENTITY] as introduced in discourse 
and which denotes the [SPECIFIC QUALITY/RELATION/STATUS] of that entity
[, as grounded in INSTITUTIONAL/SOCIAL REALITY where applicable].
```

### 1.3 The Three-Layer Distinction

Always be clear about which layer you're defining:

| Layer | What It Contains | BFO Category | Relationship |
|-------|------------------|--------------|--------------|
| **World** | Things that exist independently | Independent Continuants, Occurrents | What ICEs are *about* |
| **Information** | Content that denotes portions of reality | Generically Dependent Continuants (ICEs) | *Concretized in* bearers |
| **Bearer** | Physical/digital substrates | Information Bearing Entities (IBEs) | *Bears* concretizations of ICEs |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE ICE / IBE / WORLD RELATIONSHIP                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CRITICAL BFO NUANCE:                                                       │
│  ────────────────────                                                       │
│  Information Content Entities are GENERICALLY DEPENDENT CONTINUANTS.        │
│  They do not float free—they depend on bearers for their existence.        │
│  But they are not identical to their bearers and can migrate between them. │
│                                                                             │
│           ┌─────────────────────────────────────────────┐                  │
│           │            WORLD LAYER                      │                  │
│           │  (Independent Continuants, Occurrents)      │                  │
│           │                                             │                  │
│           │    Person ←──── DiscourseReferent ────┐     │                  │
│           │      │          is about              │     │                  │
│           │      │ participates in                │     │                  │
│           │      ▼                                │     │                  │
│           │    Treatment (process) ◄── VerbPhrase ┘     │                  │
│           │                            is about         │                  │
│           └─────────────────────────────────────────────┘                  │
│                              ▲                                              │
│                              │ is about / denotes                          │
│                              │ (mediated by discourse)                     │
│                              │ (constrained by causal-historical relation) │
│           ┌─────────────────────────────────────────────┐                  │
│           │          INFORMATION LAYER                  │                  │
│           │  (Generically Dependent Continuants)        │                  │
│           │                                             │                  │
│           │    VerbPhrase (ICE)                         │                  │
│           │      - is about: Treatment AS INTRODUCED    │                  │
│           │        IN DISCOURSE                         │                  │
│           │      - denotes: predicative content +       │                  │
│           │        temporal/modal boundaries            │                  │
│           │      - denotation: constrained, not         │                  │
│           │        guaranteed                           │                  │
│           └─────────────────────────────────────────────┘                  │
│                              │                                              │
│                              │ concretized in                              │
│                              ▼                                              │
│           ┌─────────────────────────────────────────────┐                  │
│           │           BEARER LAYER                      │                  │
│           │  (Information Bearing Entities)             │                  │
│           │                                             │
│           │    Text document, database record,          │                  │
│           │    sound wave, neural pattern               │                  │
│           └─────────────────────────────────────────────┘                  │
│                                                                             │
│  KEY INSIGHT:                                                               │
│  ────────────                                                               │
│  The same ICE UNIVERSAL may be concretized across multiple bearers.        │
│  Distinct ICE PARTICULARS may be type-identical while numerically          │
│  distinct. (This matters for counting and provenance.)                     │
│                                                                             │
│  The CONTENT (ICE type) is the same regardless of language or medium.      │
│  The CONCRETIZATION (specific pattern of ink, bits, sound) varies.         │
│  The ICE *depends on* having some bearer, but is not *identical to* it.    │
│                                                                             │
│  IMPLICATION FOR DEFINITIONS:                                               │
│  ─────────────────────────────                                              │
│  Define what the ICE DENOTES (world layer), not how it is                  │
│  CONCRETIZED (bearer layer) or EXPRESSED (linguistic form).                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Universals vs. Particulars

BFO distinguishes between **Universals** (repeatable types) and **Particulars** (individual instances).

| Kind | What It Is | Definition Task | Example |
|------|------------|-----------------|---------|
| **Universal (Class)** | A repeatable kind that can be instantiated | Specify necessary and sufficient conditions for instantiation | `VerbPhrase`, `Person`, `ActualityStatus` |
| **Particular (Individual)** | A single, non-repeatable entity | Specify what distinguishes *this* instance from siblings | `:Actual`, `:Prescribed`, `:Hypothetical` |

**When defining a Universal (Class):**

> "An X is a [Genus] that [Differentia]"
> Specifies what it takes for *any* particular to be an instance of this class.

**When defining a Particular (Individual of an enumeration):**

> "X is the instance of [Class] that indicates [specific condition/status], as distinguished from [siblings] by [criterion]"
> Specifies what distinguishes *this* individual from other individuals of the same class.

**Critical Clarification on Enumerated Individuals**:

Enumerated individuals like `:Actual`, `:Prescribed`, `:Hypothetical` are borderline Platonic unless explicitly grounded. TagTeam commits to:

> **Enumerated individuals correspond to institutionally grounded normative or ontological statuses, not abstract semantic labels.**

This means `:Prescribed` is not merely a tag we invented—it corresponds to a real normative status grounded in institutional frameworks (law, medicine, organizational policy).

**Modeling Choice Acknowledgment** (NEW in v3.1):

> Enumerated actuality statuses are treated here as named individuals for interoperability and constraint checking, though alternative models may reify them as qualities or roles inhering in occurrents. This is a modeling commitment, not a claim that the individual-based approach is uniquely correct.

This acknowledgment:
- Disarms reviewers who prefer the quality/role alternative
- Does not weaken the chosen model
- Reflects legitimate variation in BFO modeling practice

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL VS. PARTICULAR DEFINITIONS                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  UNIVERSAL (CLASS) DEFINITION:                                              │
│  ──────────────────────────────                                             │
│  :ActualityStatus                                                           │
│      skos:definition "An information content entity that is about an       │
│          occurrent as introduced in discourse and which denotes the mode   │
│          of existence or normative standing under which that occurrent     │
│          is presented, as grounded in factual, institutional, or           │
│          hypothetical frameworks."@en .                                    │
│                                                                             │
│  This tells us: what does it take for ANY particular to be an              │
│  ActualityStatus? It must be an ICE, about an occurrent as introduced      │
│  in discourse, denoting grounded mode of existence/standing.               │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  PARTICULAR (INDIVIDUAL) DEFINITION:                                        │
│  ────────────────────────────────────                                       │
│  :Prescribed                                                                │
│      a :ActualityStatus ;                                                  │
│      skos:definition "The actuality status indicating that the denoted     │
│          occurrent is obligated or required under some normative           │
│          framework, as distinguished from :Actual (factual obtaining),     │
│          :Permitted (allowed but not required), :Prohibited (forbidden),   │
│          and :Hypothetical (merely entertained)."@en .                     │
│                                                                             │
│  This tells us: what distinguishes THIS PARTICULAR status from siblings?   │
│  It indicates obligation grounded in normative frameworks.                 │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  GROUNDING NOTE:                                                            │
│  ───────────────                                                            │
│  :Prescribed is not an abstract label—it corresponds to the real           │
│  normative status of obligation as instantiated in legal codes,            │
│  medical protocols, organizational policies, etc.                          │
│                                                                             │
│  MODELING ALTERNATIVE NOTE:                                                 │
│  ──────────────────────────                                                 │
│  One could alternatively model normative standing as a quality or role     │
│  inhering in the act itself, with the ICE denoting that quality/role.      │
│  The enumerated-individual approach is chosen here for tractability        │
│  and interoperability, not as the uniquely correct BFO interpretation.     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part II: Definition Anatomy

### 2.1 Required Components

Every definition MUST include:

| Component | Description | Signals |
|-----------|-------------|---------|
| **Genus** | Immediate parent class | "A [parent class]…" |
| **Aboutness** | What portion of reality it denotes (for ICEs) | "…that is about [BFO Entity] as introduced in discourse…" |
| **Essential differentia** | What distinguishes it from siblings | "…and that denotes [specific aspect]" |

For Tier 1 (discourse-derived) ICEs, also include:

| Component | Description | Signals |
|-----------|-------------|---------|
| **Discourse-mediation qualifier** | Acknowledges mediated aboutness | "as introduced in discourse" |
| **Grounding** (for normative/modal) | Anchors denotata in institutional reality | "as grounded in [framework]" |

### 2.2 Optional Components

| Component | When to Include | Signals |
|-----------|-----------------|---------|
| **Structural characterization** | When intrinsic structure is definitional | "…and which is structured to reflect…" |
| **Relation to other classes** | When the relationship is essential | "…and is linked to [X] via [property]" |
| **Negative differentiation** | When confusion with a sibling is likely | "…rather than [what it is NOT]" |

**Caution on functional language:** Avoid "serves to" or "functions to" in differentia unless the entity necessarily has that function. Differentia should focus on **intrinsic properties**, not contingent uses.

| ❌ AVOID | ✅ PREFER |
|----------|----------|
| "…which serves to link expressions to events" | "…and which links expressions to events" |
| "…which serves to anchor identity relations" | "…and which anchors identity relations" |
| "…functions to track provenance" | "…and which includes the epistemic grounds of the assertion" |

**Caution on relations:** Relations included in definitions must themselves be essential, not merely frequent. If the relation is contingent (occurs often but not necessarily), it belongs in `rdfs:comment`, not `skos:definition`.

### 2.3 Definition Templates

**Gold Standard ICE Formula (Tier 1 / Discourse-Derived):**

```
[TERM] is an information content entity that is about some [BFO ENTITY TYPE] 
as introduced in discourse, and which denotes the [SPECIFIC QUALITY / RELATION / STATUS] 
of that entity [, as grounded in INSTITUTIONAL/SOCIAL REALITY where applicable].
```

**For Classes (Universals):**

```
[TERM] is a [GENUS] that is about [PORTION OF REALITY] as introduced in discourse 
and that denotes [DIFFERENTIA specifying what aspect of that reality], 
[constrained by DISCOURSE CONTEXT].
```

**For Individuals (Particulars in an enumeration):**

```
[TERM] is the instance of [PARENT CLASS] that indicates [SPECIFIC CONDITION OR STATUS], 
as distinguished from [siblings] by [distinguishing criterion], 
and as grounded in [INSTITUTIONAL FRAMEWORK].
```

**For Processes:**

```
[TERM] is a process in which [AGENT TYPE] [ACTION] with respect to [INPUT/PATIENT], 
resulting in [OUTPUT OR STATE CHANGE].
```

**For Process Boundaries:**

```
[TERM] is a process boundary marking the [BEGINNING/END/TRANSITION] of [PROCESS TYPE] 
at which [INSTANTANEOUS CONDITION OBTAINS].
```

---

## Part III: Anti-Patterns (What NOT to Do)

### 3.1 Circularity

**The definiendum (term being defined) must not appear in the definition.**

| ❌ BAD | ✅ GOOD |
|--------|--------|
| "A verb phrase is an ICE representing a verb phrase" | "An ICE that is about an occurrent as introduced in discourse and denotes its predicative content together with temporal and modal boundaries" |
| "A discourse referent is a linguistic reference" | "An ICE that is about a particular as introduced through a referring expression" |
| "An assertion event is when an assertion is made" | "A process in which an agent produces an ICE together with its epistemic grounds" |

**Also avoid:**
- Synonyms of the term ("A prohibition is a forbidding")
- Morphological variants ("To prescribe is to make a prescription")
- Near-synonyms that don't add information ("An obligation is a duty")

### 3.2 Missing Aboutness

**Every ICE definition must specify what it denotes.**

| ❌ BAD | ✅ GOOD |
|--------|--------|
| "An ICE extracted from text" | "An ICE that is about [X] as introduced in discourse" |
| "An ICE representing linguistic structure" | "An ICE that is about [worldly referent] and denotes [specific aspect]" |
| "An ICE encoding grammatical features" | "An ICE that is about an occurrent as introduced in discourse and denotes its temporal and modal boundaries" |

### 3.3 Process-Product Confusion

**Don't conflate the process of extraction with the entity extracted.**

| ❌ BAD | ✅ GOOD |
|--------|--------|
| "An ICE created by parsing" | "An ICE that is about [X]" (creation is provenance, not definition) |
| "The result of NER" | "An ICE that is about a named particular as introduced in discourse" |
| "An artifact of semantic analysis" | "An ICE that denotes [specific aspect of reality]" |

The definition specifies what the entity IS, not how it came to be. Provenance belongs in `rdfs:comment` or dedicated provenance properties.

### 3.4 Genus Too Broad or Too Narrow

| Problem | Example | Fix |
|---------|---------|-----|
| **Too broad** | "A thing that represents meaning" | Use specific BFO/CCO parent: "An information content entity that…" |
| **Too narrow** | "A cco:DirectiveICE that uses modal verbs" | Modals are expression, not essence: "…that directs an agent to perform an act" |

**The "So What?" Test:** Remove the differentia. Does the definition still uniquely identify your class? If not, your genus is doing all the work and your differentia is vacuous.

### 3.5 Differentia That Don't Differentiate

**The differentia must distinguish from sibling classes.**

| ❌ BAD | Why | ✅ GOOD |
|--------|-----|--------|
| "An ICE found in documents" | All ICEs can be in documents | "An ICE that denotes [specific X]" |
| "An ICE with provenance" | All TagTeam ICEs have provenance | "An ICE that denotes [specific X]" |
| "An ICE used in NLP" | That's application, not essence | "An ICE that denotes [specific X]" |

**The Mutual Exclusivity Check:** Does your definition clearly exclude sibling classes?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MUTUAL EXCLUSIVITY CHECK                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TEST: Can an entity satisfy BOTH your definition AND a sibling's?         │
│                                                                             │
│  EXAMPLE - Checking DeonticContent vs. DescriptiveContent:                  │
│                                                                             │
│  DeonticContent:                                                            │
│    "An ICE that is about an act as introduced in discourse and denotes     │
│     its normative status (whether it ought, may, or must not occur)."      │
│                                                                             │
│  DescriptiveContent:                                                        │
│    "An ICE that is about a state of affairs as introduced in discourse     │
│     and denotes whether that state of affairs obtains as a matter of       │
│     fact."                                                                 │
│                                                                             │
│  CHECK: Can something denote BOTH normative status AND factual obtaining   │
│         in the same respect?                                                │
│                                                                             │
│  ANSWER: No. "Ought" and "is" are distinct modes. ✓ Mutually exclusive.   │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  CRITICAL QUALIFIER:                                                        │
│  ───────────────────                                                        │
│  Mutual exclusivity applies at the level of the PRIMARY DENOTATIONAL       │
│  ASPECT, not to composite or structured ICEs.                              │
│                                                                             │
│  A legal finding may include both descriptive claims (what happened) and   │
│  deontic claims (what ought to follow). These are COMPOSITE ICEs with      │
│  distinct components, not violations of mutual exclusivity.                │
│                                                                             │
│  The test is: "In the SAME RESPECT, can one ICE satisfy both?"            │
│  If the answer requires "well, in different respects..." then the          │
│  definitions are fine—you have a composite, not a category violation.      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Epistemological vs. Ontological

**Define what the entity IS, not how we know about it.**

| ❌ BAD (Epistemological) | ✅ GOOD (Ontological) |
|--------------------------|----------------------|
| "An ICE detected by pattern matching" | "An ICE that is about a normative principle" |
| "An ICE recognized through linguistic markers" | "An ICE that denotes scarcity of a resource relative to demand" |
| "An ICE identified by the parser" | "An ICE that is about an occurrent and denotes its modal constraints" |

Detection method belongs in `rdfs:comment`, not `skos:definition`.

### 3.7 Linguistic vs. Ontological

**Define what the entity denotes, not how it is expressed.**

| ❌ BAD (Linguistic) | ✅ GOOD (Ontological) |
|---------------------|----------------------|
| "An ICE encoded using modal verbs" | "An ICE that denotes normative necessity or possibility" |
| "An ICE expressed in past tense" | "An ICE that denotes an occurrent as temporally prior to the utterance" |
| "An ICE structured as a noun phrase" | "An ICE that is about a continuant as introduced into discourse" |

The linguistic form is how the ICE is *concretized*; the definition should specify what it *denotes*.

### 3.8 Naive Referentialism

**Don't imply that parsing directly discovers worldly entities.**

| ❌ BAD (Naive Referentialism) | ✅ GOOD (Mediated Aboutness) |
|-------------------------------|------------------------------|
| "An ICE that is about an occurrent" | "An ICE that is about an occurrent **as introduced in discourse**" |
| "An ICE that denotes a person" | "An ICE that is about a person **as referred to in discourse**" |

The qualifier acknowledges that:
- Aboutness is mediated by discourse context
- The same expression may denote different entities in different contexts
- Denotation may fail (fiction, failed reference, non-referential use)
- Mediation is causally and historically constrained (not free-floating)

### 3.9 Functional Language (Tightened in v3.1)

**Avoid "serves to" constructions; prefer direct predication.**

| ❌ AVOID | ✅ PREFER |
|----------|----------|
| "which serves to anchor identity and coreference relations" | "and which anchors identity and coreference relations" |
| "which serves to link expressions to their referents" | "and which links expressions to their referents" |
| "which serves to mark temporal boundaries" | "and which marks temporal boundaries" |

"Serves to" implies contingent function rather than essential structure. Direct predication is cleaner ontology.

---

## Part IV: BFO/CCO-Specific Rules

### 4.1 Use BFO Terminology Correctly

| Term | BFO Meaning | Use For |
|------|-------------|---------|
| **Continuant** | Entity that persists through time (has no temporal parts) | Persons, objects, qualities, roles |
| **Occurrent** | Entity that unfolds in time (has temporal parts) | Events, processes, temporal regions |
| **Particular** | An individual entity (non-repeatable) | Specific persons, specific events |
| **Universal** | A repeatable kind (type) | Person (the type), Event (the type) |
| **Quality** | A specifically dependent continuant that inheres in a bearer | Color, temperature, illness severity |
| **Role** | A realizable entity externally grounded | Patient role, agent role |
| **Function** | A realizable entity internally grounded | Heart's pumping function |
| **Process** | An occurrent with proper temporal parts | Treatment, assertion, detection |
| **Process Boundary** | A zero-dimensional temporal entity | Instant of death, moment of signing |
| **Generically Dependent Continuant** | An entity that depends on a bearer but can migrate between bearers | Information content entities |

### 4.2 Process vs. Process Boundary

In NLP and event extraction, it is critical to distinguish **processes** (which have duration) from **process boundaries** (which are instantaneous).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROCESS VS. PROCESS BOUNDARY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROCESS (bfo:Process)                                                      │
│  ─────────────────────                                                      │
│  • Has temporal parts (beginning, middle, end)                             │
│  • Has duration                                                             │
│  • Can be divided into sub-processes                                       │
│                                                                             │
│  Examples:                                                                  │
│    - Treatment (has duration, phases)                                      │
│    - Employment (extends over time)                                        │
│    - Trial (has proceedings, verdict)                                      │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  PROCESS BOUNDARY (bfo:ProcessBoundary)                                     │
│  ───────────────────────────────────────                                    │
│  • Zero-dimensional in time (an instant)                                   │
│  • Marks a transition or threshold                                         │
│  • Cannot be divided                                                        │
│                                                                             │
│  Examples:                                                                  │
│    - Start of employment (the instant hiring takes effect)                 │
│    - Moment of death (the transition from alive to dead)                   │
│    - Point of contract signing (the instant obligation begins)             │
│    - Threshold crossing (the instant a limit is exceeded)                  │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  FIAT BOUNDARIES (important nuance):                                        │
│  ───────────────────────────────────                                        │
│  Some legally or institutionally salient "moments" are FIAT BOUNDARIES     │
│  grounded in institutional rules, not physical instants.                   │
│                                                                             │
│  Example: "The moment the contract takes effect" may be defined as         │
│  midnight on a certain date by legal convention, not by any physical       │
│  transition. It is still a ProcessBoundary, but its identity conditions    │
│  are institutionally determined.                                           │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  RULE OF THUMB:                                                             │
│  ───────────────                                                            │
│  Ask: "Does this have a beginning, middle, and end?"                       │
│                                                                             │
│    YES → Process                                                           │
│    NO (it's just an instant of transition) → Process Boundary              │
│                                                                             │
│  TAGTEAM IMPLICATION:                                                       │
│  ─────────────────────                                                      │
│  When TagTeam extracts events, distinguish:                                │
│    - "The treatment lasted three weeks" → Process                          │
│    - "The patient died at 3:42 PM" → Process Boundary                      │
│    - "The contract takes effect on January 1" → Fiat Process Boundary      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 ICE Subtypes in CCO

Know which CCO ICE subtype your class belongs under:

| CCO Class | Use When Entity Denotes | Key Differentiator |
|-----------|-------------------------|-------------------|
| `cco:DescriptiveInformationContentEntity` | How things are (facts) | Word-to-world direction of fit |
| `cco:DirectiveInformationContentEntity` | How things should be (norms, commands) | World-to-word direction of fit |
| `cco:DesignativeInformationContentEntity` | Names and identifiers | Conventional reference |
| `cco:InformationContentEntity` (generic) | When no subtype fits precisely | Use sparingly |

**Direction of Fit: Heuristic Status and Grounding** (Clarified in v3.1):

Direction of fit is a useful **heuristic** for classification, but it is **not itself an ontological property** recognized by BFO. It is a philosophical tool imported from speech act theory (Searle, Anscombe).

| Direction | Meaning | Use |
|-----------|---------|-----|
| **Word-to-world** | The content aims to match reality | Classify as Descriptive |
| **World-to-word** | Reality is meant to match the content | Classify as Directive |

> **Critical Clarification**: Direction of fit **supervenes on the grounding relations** of the denoted content, not on speaker intentions or linguistic form. Descriptive ICEs are grounded in factual states of affairs; Directive ICEs are grounded in institutional normative frameworks. The direction-of-fit heuristic tracks this grounding distinction.

This clarification:
- Locks direction-of-fit back into realism
- Prevents importing speech-act theory as primitive ontology
- Maintains classification utility without ontological overcommitment

### 4.4 Realization and Roles

When defining roles and their realization:

| Situation | Property | Example |
|-----------|----------|---------|
| Role is actually realized | `bfo:realized_in` | Doctor role realized in actual treatment |
| Role would be realized if act occurred | `:would_be_realized_in` | Doctor role would be realized in prescribed treatment |
| Entity bears the role | `bfo:bearer_of` | Person bears doctor role |

### 4.5 Concretization

For ICEs, understand the concretization relationship:

| Relationship | Meaning | Example |
|--------------|---------|---------|
| ICE `concretized_in` IBE | The content is physically realized in a bearer | VerbPhrase concretized in text document |
| Same ICE type, multiple concretizations | Same content type in different bearers | Same proposition type in English and German |
| IBE `bears` concretization | The physical substrate carries the pattern | PDF file bears the text pattern |

---

## Part V: The Checklist

Use this checklist for every definition before committing:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEFINITION QUALITY CHECKLIST v3.1                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STRUCTURAL REQUIREMENTS                                                    │
│  ─────────────────────────                                                  │
│  □ Genus is the IMMEDIATE parent class (not grandparent)                   │
│  □ Genus uses proper BFO/CCO terminology                                   │
│  □ Differentia is present and substantive                                  │
│  □ Differentia distinguishes from ALL sibling classes                      │
│  □ Definition is a single sentence (may be complex, not run-on)            │
│                                                                             │
│  ABOUTNESS (FOR ICEs)                                                       │
│  ────────────────────                                                       │
│  □ Definition specifies what the ICE DENOTES                               │
│  □ Uses "is about" or "denotes" (not "represents" or "encodes")           │
│  □ Aboutness refers to BFO entities (continuant, occurrent, quality)       │
│  □ Specifies WHICH ASPECT of that entity is denoted                        │
│                                                                             │
│  DISCOURSE-MEDIATION (FOR TIER 1 ICEs)                                      │
│  ──────────────────────────────────────                                     │
│  □ Includes "as introduced in discourse" or equivalent qualifier           │
│  □ Acknowledges that denotation is constrained, not guaranteed             │
│  □ Does NOT imply parsing directly discovers worldly entities              │
│  □ Respects causal-historical constraint on admissible denotation targets  │
│                                                                             │
│  GROUNDING (FOR NORMATIVE/MODAL DENOTATA)                                   │
│  ─────────────────────────────────────────                                  │
│  □ Normative statuses grounded in institutional/social reality             │
│  □ Modal aspects grounded in discourse context or institutional rules      │
│  □ Not merely linguistic or cognitive constructs                           │
│                                                                             │
│  ANTI-PATTERN CHECKS                                                        │
│  ───────────────────                                                        │
│  □ Term being defined does NOT appear in definition                        │
│  □ No synonyms or morphological variants of the term                       │
│  □ No "extracted from" / "detected by" / "identified as" (epistemological)│
│  □ No "encoded as" / "expressed via" / "structured as" (linguistic)        │
│  □ No "serves to" / "functions to" (use direct predication instead)        │
│  □ No application context ("used in NLP") as definitional                  │
│  □ No naive referentialism (implies direct ontological discovery)          │
│                                                                             │
│  THE "SO WHAT?" TEST                                                        │
│  ────────────────────                                                       │
│  □ Differentia could NOT apply to parent class without losing meaning      │
│  □ Removing differentia would NOT still uniquely identify the class        │
│                                                                             │
│  MUTUAL EXCLUSIVITY CHECK                                                   │
│  ─────────────────────────                                                  │
│  □ Definition clearly EXCLUDES sibling classes                             │
│  □ No entity could satisfy both this definition AND a sibling's            │
│  □ (Check applies at PRIMARY DENOTATIONAL ASPECT, not to composites)       │
│                                                                             │
│  UNIVERSAL VS. PARTICULAR                                                   │
│  ────────────────────────                                                   │
│  □ If CLASS: defines conditions for ANY particular to instantiate          │
│  □ If INDIVIDUAL: defines what distinguishes THIS instance from siblings   │
│  □ If ENUMERATED INDIVIDUAL: grounded in institutional reality             │
│  □ OWL metadata correct (owl:Class vs. owl:NamedIndividual)               │
│                                                                             │
│  PROCESS VS. PROCESS BOUNDARY (for occurrents)                              │
│  ─────────────────────────────────────────────                              │
│  □ If has duration → classified as Process                                 │
│  □ If instantaneous transition → classified as ProcessBoundary             │
│  □ If institutionally defined instant → noted as fiat boundary             │
│                                                                             │
│  CLARITY                                                                    │
│  ───────                                                                    │
│  □ A BFO expert would recognize proper usage of terms                      │
│  □ A domain expert could understand without TagTeam context                │
│  □ No undefined jargon or project-specific terms in definition             │
│  □ Technical details in rdfs:comment, not skos:definition                  │
│                                                                             │
│  COMPLETENESS                                                               │
│  ────────────                                                               │
│  □ skos:definition contains the formal Aristotelian definition             │
│  □ rdfs:comment contains supplementary explanation                         │
│  □ rdfs:comment explains Tier 1/Tier 2 relationship if relevant           │
│  □ rdfs:comment notes constrained/fallible denotation where applicable     │
│  □ skos:example provided for complex or potentially confusing classes      │
│                                                                             │
│  CONSISTENCY                                                                │
│  ───────────                                                                │
│  □ Parallel classes use parallel definition structure                      │
│  □ Terminology consistent with rest of ontology                            │
│  □ No contradiction with parent class definition                           │
│  □ No contradiction with sibling class definitions                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part VI: Worked Examples

### Example 1: VerbPhrase (The Hard Case)

**Original (Problematic):**

```turtle
:VerbPhrase
    skos:definition "An information content entity representing a verb phrase 
        extracted from text, including its lemma, tense, aspect, and 
        modality markers."@en .
```

**Checklist Failures:**
- ❌ "verb phrase" appears in definition (circularity)
- ❌ No aboutness specified
- ❌ "extracted from text" is epistemological
- ❌ "including its lemma…" describes data model, not essence
- ❌ "representing" is vague
- ❌ No discourse-mediation qualifier
- ❌ Implies naive referentialism

**Fixed (Gold Standard with Critique Integration):**

```turtle
:VerbPhrase
    a owl:Class ;
    rdfs:subClassOf cco:InformationContentEntity ;
    rdfs:label "Verb Phrase"@en ;
    skos:definition """An information content entity that is about an occurrent 
        as introduced in discourse, and which denotes the predicative content 
        of that occurrent together with the temporal and modal boundaries of 
        its obtaining."""@en ;
    rdfs:comment """VerbPhrases are Tier 1 discourse-derived ICEs. Their 
        denotation is constrained by the discourse context in which they are 
        introduced—the same predicative expression may denote different 
        occurrents in different contexts, or fail to denote if the discourse 
        is non-referential (e.g., fiction, hypotheticals). Grammatical features 
        (tense, aspect, modality) carried by the linguistic bearer constrain 
        but do not determine the denoted occurrent's temporal and modal status. 
        Link to Tier 2 worldly entities via :denotesOccurrent where denotation 
        succeeds."""@en ;
    skos:example """The expression 'should have been treating' introduces a 
        VerbPhrase that is about a treatment occurrent, denoting it as: 
        (a) past-oriented (anterior), (b) durative (progressive aspect), and 
        (c) obligated (deontic modality). Whether this VerbPhrase successfully 
        denotes a real treatment depends on discourse context."""@en .
```

**Why This Works:**

| Requirement | How It's Met |
|-------------|--------------|
| Genus | "information content entity" |
| Aboutness | "is about an occurrent" |
| Discourse-mediation | "as introduced in discourse" |
| Differentia | "denotes predicative content together with temporal and modal boundaries" |
| No circularity | "verb phrase" absent from definition |
| Constrained denotation | rdfs:comment explicitly notes fallibility |
| Tier 1/Tier 2 link | rdfs:comment explains relationship |

---

### Example 2: DeonticContent with Grounding

**Definition:**

```turtle
:DeonticContent
    a owl:Class ;
    rdfs:subClassOf cco:InformationContentEntity ;
    rdfs:label "Deontic Content"@en ;
    skos:definition """An information content entity that is about an act as 
        introduced in discourse, and which denotes the normative status of 
        that act—whether it is obligated, permitted, or prohibited—as 
        grounded in institutional, legal, or social frameworks."""@en ;
    rdfs:comment """DeonticContent has world-to-word direction of fit 
        (heuristically speaking): it specifies how the world ought to be, not 
        how it is. This direction-of-fit classification supervenes on the 
        grounding relation: DeonticContent is grounded in institutional 
        normative frameworks rather than factual states of affairs. The 
        normative status denoted is not a mere linguistic label but 
        corresponds to real institutional facts—obligations created by 
        law, policy, contract, or social norm. Denotation success depends on 
        whether the discourse successfully refers to a real normative 
        framework."""@en .
```

**Key Features:**
- ✅ Discourse-mediation: "as introduced in discourse"
- ✅ Grounding: "as grounded in institutional, legal, or social frameworks"
- ✅ Direction of fit noted as heuristic, supervening on grounding
- ✅ Mutual exclusivity with DescriptiveContent (ought vs. is)

---

### Example 3: Enumerated Individual with Grounding

**Class:**

```turtle
:ActualityStatus
    a owl:Class ;
    rdfs:subClassOf cco:InformationContentEntity ;
    skos:definition """An information content entity that is about an occurrent 
        as introduced in discourse, and which denotes the mode of existence or 
        normative standing under which that occurrent is presented—whether as 
        actual, prescribed, permitted, prohibited, hypothetical, or negated—as 
        grounded in factual circumstances or institutional frameworks."""@en ;
    rdfs:comment """Enumerated actuality statuses are treated here as named 
        individuals for interoperability and constraint checking. Alternative 
        models may reify them as qualities or roles inhering in occurrents; 
        the individual-based approach is a modeling commitment, not a claim 
        of unique correctness."""@en .
```

**Individual:**

```turtle
:Prescribed
    a owl:NamedIndividual, :ActualityStatus ;
    rdfs:label "Prescribed"@en ;
    skos:definition """The actuality status indicating that the denoted 
        occurrent is obligated or required under some normative framework, 
        as distinguished from :Actual (factual obtaining), :Permitted 
        (allowed but not required), :Prohibited (forbidden), and 
        :Hypothetical (merely entertained), and as grounded in institutional 
        rules such as law, medical protocol, or organizational policy."""@en ;
    rdfs:comment """Triggered by deontic necessity markers such as 'must', 
        'shall', 'is required to', 'ought to'. The grounding requirement 
        means :Prescribed is not an abstract semantic label but corresponds 
        to real normative obligations instantiated in institutional 
        frameworks."""@en .
```

**Key Features:**
- ✅ Distinguishes from all siblings explicitly
- ✅ Grounded in institutional reality
- ✅ Linguistic triggers relegated to rdfs:comment
- ✅ Modeling choice acknowledged in class comment

---

### Example 4: DiscourseReferent (Functional Language Fixed)

```turtle
:DiscourseReferent
    a owl:Class ;
    rdfs:subClassOf cco:InformationContentEntity ;
    rdfs:label "Discourse Referent"@en ;
    skos:definition """An information content entity that is about a particular 
        (either a continuant or an occurrent) as introduced into discourse 
        through a referring expression, and which anchors identity and 
        coreference relations across a text."""@en ;
    rdfs:comment """DiscourseReferents are distinguished from VerbPhrases in 
        that they REFER rather than PREDICATE: they introduce and track 
        particulars in discourse, while VerbPhrases predicate properties of 
        those particulars. The same linguistic expression may introduce a 
        DiscourseReferent in one context and fail to refer in another 
        (fiction, hypotheticals, failed reference). Link to Tier 2 worldly 
        entities via :denotesParticular where reference succeeds."""@en ;
    skos:example """The expression 'the patient' introduces a DiscourseReferent 
        that is about a person. Subsequent mentions ('she', 'the woman') may 
        corefer with this DiscourseReferent, maintaining identity across the 
        text."""@en .
```

**Change from v3.0:** "which serves to anchor" → "and which anchors"

**Mutual Exclusivity Check with VerbPhrase:**
- DiscourseReferent: REFERS to particulars (introduces them into discourse)
- VerbPhrase: PREDICATES properties of occurrents (what happens, when, how)
- ✅ Reference vs. predication is a robust distinction
- ✅ Mutually exclusive at primary denotational aspect

---

## Part VII: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEFINITION QUICK REFERENCE v3.1                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GOLD STANDARD ICE FORMULA (TIER 1):                                        │
│  ────────────────────────────────────                                       │
│  "An ICE that is about some [BFO Entity] AS INTRODUCED IN DISCOURSE        │
│   and which denotes the [specific quality/relation/status] of that         │
│   entity [, as grounded in INSTITUTIONAL REALITY where applicable]."       │
│                                                                             │
│  KEY QUALIFIERS:                                                            │
│  ────────────────                                                           │
│  • "as introduced in discourse" — prevents naive referentialism            │
│  • "as grounded in [framework]" — anchors normative/modal denotata         │
│  • Causal-historical constraint — blocks free-floating aboutness           │
│  • rdfs:comment notes constrained/fallible denotation                      │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  FORBIDDEN IN skos:definition:            ALLOWED IN rdfs:comment:          │
│  • The term itself                        • Detection methods              │
│  • Synonyms / variants                    • Linguistic triggers            │
│  • "extracted" / "detected"               • Implementation notes           │
│  • "encoded" / "expressed as"             • Tier 1/Tier 2 relationships   │
│  • "serves to" (use direct predication)   • Constrained denotation notes  │
│  • "in NLP" / "in parsing"                • Examples of concretization     │
│  • Naive referentialism                   • Fallibility acknowledgment     │
│                                           • Modeling choice notes          │
│                                                                             │
│  REQUIRED IN skos:definition (for Tier 1 ICEs):                            │
│  • "is about" or "denotes"                                                 │
│  • Reference to BFO category                                               │
│  • "as introduced in discourse" qualifier                                  │
│  • Grounding clause (for normative/modal)                                  │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  FOUR CRITICAL TESTS:                                                       │
│                                                                             │
│  1. ABOUTNESS TEST                                                          │
│     "This ICE denotes ___." Fill with BFO entity, not linguistic structure │
│                                                                             │
│  2. SO WHAT? TEST                                                           │
│     Remove differentia. Does definition still work? If yes → TOO BROAD     │
│                                                                             │
│  3. MUTUAL EXCLUSIVITY TEST                                                 │
│     Could entity satisfy both this AND sibling? If yes → FIX IT            │
│     (Applies at PRIMARY DENOTATIONAL ASPECT)                               │
│                                                                             │
│  4. NAIVE REFERENTIALISM TEST                                               │
│     Does definition imply parsing discovers worldly entities directly?     │
│     If yes → Add "as introduced in discourse" qualifier                    │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  PHILOSOPHICAL COMMITMENTS:                                                 │
│                                                                             │
│  • Linguistic entities ARE real (have causal powers, persistence)          │
│  • They ARE ICEs (GDCs concretized in bearers)                             │
│  • Aboutness IS discourse-mediated (not direct world-access)               │
│  • Mediation IS causally-historically constrained (not free-floating)      │
│  • Denotation IS constrained, not guaranteed                               │
│  • Normative denotata ARE grounded in institutional reality                │
│  • Enumerated individuals ARE NOT abstract labels                          │
│  • Direction of fit SUPERVENES on grounding, not intentions                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Glossary of BFO Terms for Definers

| Term | Definition | When to Use in Definitions |
|------|------------|---------------------------|
| **is about** | The intentional relation between an ICE and what it denotes | "An ICE that is about [X] as introduced in discourse" |
| **denotes** | Synonym for "is about"; the denotation relation | "…and which denotes the [aspect] of that [X]" |
| **inheres in** | Relation between a dependent continuant and its bearer | "A quality that inheres in [bearer]" |
| **realized in** | Relation between a realizable and the process that realizes it | "A role realized in [process]" |
| **concretized in** | Relation between a GDC and the IBE bearing it | "An ICE concretized in [bearer]" |
| **participates in** | Relation between a continuant and a process | "[Continuant] participates in [process]" |
| **has participant** | Inverse of participates in | "[Process] has participant [continuant]" |
| **bearer of** | Inverse of inheres in | "[Independent continuant] is bearer of [dependent continuant]" |
| **grounded in** | Relation anchoring normative/modal entities to institutional reality | "as grounded in [institutional framework]" |

---

## Appendix B: Common Definition Patterns by Class Type

| Class Type | Pattern | Example |
|------------|---------|---------|
| **Tier 1 ICE about continuant** | "An ICE that is about a [continuant type] as introduced in discourse and which denotes [quality/relation]" | "An ICE that is about a person as referred to in discourse and which denotes their social role" |
| **Tier 1 ICE about occurrent** | "An ICE that is about an [occurrent type] as introduced in discourse and which denotes [temporal/modal aspect]" | "An ICE that is about a process as introduced in discourse and which denotes its temporal and modal boundaries" |
| **Deontic ICE** | "An ICE that is about an act as introduced in discourse and which denotes its normative status, as grounded in [framework]" | "An ICE that is about a medical act as introduced in discourse and which denotes its obligatoriness under clinical protocols" |
| **Enumerated Individual** | "The [parent class] indicating [specific status], as distinguished from [siblings], and as grounded in [framework]" | "The actuality status indicating obligation, as distinguished from permission and prohibition, and as grounded in institutional rules" |
| **Process** | "A process in which [agent] [action] [patient] resulting in [output]" | "A process in which a parser analyzes text resulting in a semantic graph" |
| **Process Boundary** | "A process boundary marking the instant at which [transition]" | "A process boundary marking the instant at which a contract takes effect" |
| **Fiat Boundary** | "A process boundary marking the institutionally defined instant at which [transition], as determined by [institutional rule]" | "A fiat boundary marking midnight January 1 as the instant contract obligations commence, as defined by the contract terms" |

---

## Appendix C: Philosophical Position Statement (For Ontology Header)

Include this or equivalent in the ontology file header:

```turtle
<http://tagteam.fandaws.org/ontology/>
    rdfs:comment """
PHILOSOPHICAL POSITION: REALISM ABOUT DISCOURSE-DERIVED INFORMATION CONTENT

TagTeam takes a realist stance toward linguistic information entities. This 
guide ensures definitions meet the standards required to defend this position 
against strict BFO/CCO realist critique.

CORE COMMITMENTS:

1. Linguistic entities (utterances, inscriptions, their structural components) 
   ARE real—they have physical instantiation, causal powers, identity 
   conditions, and persistence.

2. They ARE Information Content Entities—Generically Dependent Continuants 
   concretized in bearers but not identical to those bearers.

3. Their aboutness IS DISCOURSE-MEDIATED. They are about worldly entities AS 
   INTRODUCED IN DISCOURSE, not directly about mind-independent reality 
   unmediated by communicative context. The phrase "as introduced in discourse" 
   is critical: it acknowledges mediation without abandoning realism, since 
   discourse introduction is itself a real event.

4. Discourse mediation IS CAUSALLY-HISTORICALLY CONSTRAINED. Discourse 
   introduces candidates for denotation, but admissible targets are constrained 
   by causal, historical, or institutional relations to the world. This blocks 
   free-floating "aboutness" while preserving space for fiction, error, and 
   hypothesis.

5. Denotation IS CONSTRAINED, NOT GUARANTEED. Grammatical and semantic features 
   constrain interpretation, but successful denotation depends on discourse 
   context, speaker intent, and referential success. Denotation may fail in 
   non-referential contexts (fiction, hypotheticals, failed reference).

6. Normative and modal denotata REQUIRE GROUNDING in socially or institutionally 
   real entities. Enumerated individuals like :Prescribed correspond to 
   institutionally grounded normative statuses, not abstract semantic labels. 
   (Alternative modelings as qualities or roles are acknowledged as legitimate 
   BFO options; the individual-based approach is chosen for tractability.)

7. Direction of fit SUPERVENES ON GROUNDING RELATIONS, not on speaker intentions 
   or linguistic form. It is a heuristic for classification, not an ontological 
   property.

8. The method of identification (parsing, NLP) does NOT determine ontological 
   status. We identify electrons via cloud chambers; that doesn't make them 
   cloud chamber artifacts. Similarly, identifying VerbPhrases via grammatical 
   analysis doesn't make them "merely grammatical."

9. A realist ontology that is UNABLE TO ADEQUATELY REPRESENT linguistic 
   information leaves provenance unrepresentable and severs the link between 
   information and world. Language is part of reality.

TagTeam's Tier 1 classes (VerbPhrase, DiscourseReferent, DeonticContent, etc.) 
are therefore legitimate subclasses of cco:InformationContentEntity. They 
represent the informational structures through which we access knowledge of 
worldly entities (Tier 2).

This is a BFO/CCO-Aligned Ontological Definition Guide for Discourse-Derived ICEs.
"""@en .
```

---

## Appendix D: Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| **3.1** | 2026-01-23 | Causal-historical constraint on discourse mediation; direction-of-fit grounding clarification; enumerated individuals modeling acknowledgment; functional language tightening ("serves to" → direct predication); softened "failed" → "unable to adequately represent" |
| **3.0** | 2026-01-23 | Initial Smithian critique integration; discourse-mediation qualifier; constrained denotation; institutional grounding; fallibilism note; direction-of-fit disclaimer; fiat boundary nuance; philosophical position statement |
| **2.0** | 2026-01-23 | GDC/IBE nuance; process boundary distinction; refined ICE formula with "denotes"; mutual exclusivity check; universal vs. particular clarity; "So What?" test |
| **1.0** | — | Initial version |

---

**End of Document**

*Version 3.1 integrates additional Smithian realist critique feedback. This document demonstrates an unusually deep and correct understanding of BFO realism, information entities, and the ontology/epistemology boundary. The proposed conventions are defensible, internally coherent, and practically valuable.*
