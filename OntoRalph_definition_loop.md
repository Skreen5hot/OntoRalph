## MVP Ralph Loop for Ontology Definitions

### One File, One Prompt, One Loop

Create this single file in your project:

#### `ralph-loop-mvp.md`

```markdown
# Ralph Loop MVP: Definition Validator

**Version**: 1.0
**Purpose**: Iteratively refine ontology definitions until they pass quality checks.

---

## The Loop (4 Phases)

```
[GENERATE] ──► [CRITIQUE] ──► [REFINE] ──► [VERIFY]
                                              │
                                              ▼
                                         Pass? ──► Done
                                              │
                                              No
                                              │
                                              ▼
                                         Loop back (max 5x)
```

---

## The Checklist (Condensed)

Use this for CRITIQUE and VERIFY phases:

### Core Requirements (Must Pass All)
- [ ] **C1: No Circularity** - Term being defined doesn't appear in definition
- [ ] **C2: Has Genus** - Names immediate parent class
- [ ] **C3: Has Differentia** - Distinguishes from sibling classes
- [ ] **C4: Ontological** - Defines what it IS, not how we find/use it

### ICE Requirements (If Information Content Entity)
- [ ] **I1: Aboutness** - Specifies what it denotes ("is about X")
- [ ] **I2: BFO Target** - X is a BFO entity type (continuant, occurrent, quality)
- [ ] **I3: Discourse Qualifier** - Includes "as introduced in discourse" or equivalent

### Quality Checks
- [ ] **Q1: So-What Test** - Differentia couldn't apply to parent class unchanged
- [ ] **Q2: Exclusivity** - Definition excludes sibling classes
- [ ] **Q3: Expert Test** - A BFO expert would approve the terminology

### Red Flags (Auto-Fail if Present)
- [ ] **R1**: Contains "extracted", "detected", "identified", "parsed"
- [ ] **R2**: Contains "represents" (use "denotes" instead)
- [ ] **R3**: Contains "serves to", "used to", "functions to"
- [ ] **R4**: References linguistic form ("noun phrase", "encoded as")

---

## Scoring

- **PASS**: All Core (C1-C4) + All applicable ICE (I1-I3) + No Red Flags
- **FAIL**: Any Core fails OR any Red Flag present
- **ITERATE**: Quality checks fail but Core passes (worth fixing)

---

## Quick Reference: Good Definition Patterns

**For ICE classes:**
```
A [parent ICE class] that is about [BFO entity type] as introduced in 
discourse, and which denotes [specific aspect of that entity].
```

**For other classes:**
```
A [parent class] that [essential distinguishing property].
```

**For enumerated individuals:**
```
The [parent class] indicating [specific status], as distinguished from 
[siblings] by [criterion].
```
```

---

### The Master Prompt

Copy this entire block and paste into Claude with your class information filled in:

```markdown
# Ralph Loop: Definition Rewrite

## Task
Iteratively improve this ontology class definition until it passes all quality checks.

## Class Information
- **Class IRI**: [FILL IN, e.g., :DocumentContent]
- **Label**: [FILL IN, e.g., "Document Content"]
- **Parent Class**: [FILL IN, e.g., cco:InformationContentEntity]
- **Sibling Classes**: [FILL IN, e.g., :RecordContent, :StatementContent]
- **Is this an ICE?**: [Yes/No]

## Current Definition
```
[PASTE CURRENT DEFINITION HERE, or "None" if new class]
```

## Instructions

Execute this loop:

### GENERATE
Write an improved definition following this pattern:
- For ICEs: "A [parent] that is about [BFO entity] as introduced in discourse, and which denotes [specific aspect]."
- For others: "A [parent] that [differentia]."

### CRITIQUE
Apply this checklist to your generated definition:

**Core Requirements:**
- [ ] C1: No Circularity - term not in definition
- [ ] C2: Has Genus - immediate parent named
- [ ] C3: Has Differentia - distinguishes from siblings
- [ ] C4: Ontological - what it IS, not how found/used

**ICE Requirements (if applicable):**
- [ ] I1: Aboutness - "is about" something
- [ ] I2: BFO Target - about a BFO entity type
- [ ] I3: Discourse Qualifier - "as introduced in discourse"

**Red Flags (any = auto-fail):**
- [ ] R1: "extracted/detected/identified/parsed"
- [ ] R2: "represents" (should be "denotes")
- [ ] R3: "serves to/used to/functions to"  
- [ ] R4: linguistic terms ("noun phrase", "encoded as")

List all failures with specific evidence.

### REFINE
Fix every issue found. Show the revised definition.

### VERIFY
Re-run the checklist on refined version. 
- If all Core + ICE pass and no Red Flags: **PASS** → Output final
- If any fail: **FAIL** → Loop again (iteration 2, 3... up to 5)

## Output Format

For each iteration show:
```
### Iteration N

**GENERATE:**
[definition]

**CRITIQUE:**
- C1: ✓/✗ [evidence]
- C2: ✓/✗ [evidence]
... [all items]
Issues found: [list]

**REFINE:**
[revised definition]

**VERIFY:** PASS/FAIL
[If FAIL, continue to next iteration]
```

When PASS, output:
```turtle
:[ClassName]
    a owl:Class ;
    rdfs:subClassOf [parent] ;
    rdfs:label "[Label]"@en ;
    skos:definition """[final definition]"""@en .
```
```

---

### Example Usage

Here's what it looks like in practice:

**You paste this into Claude:**

```markdown
# Ralph Loop: Definition Rewrite

## Task
Iteratively improve this ontology class definition until it passes all quality checks.

## Class Information
- **Class IRI**: :VerbPhrase
- **Label**: "Verb Phrase"
- **Parent Class**: cco:InformationContentEntity
- **Sibling Classes**: :NounPhrase, :DiscourseReferent
- **Is this an ICE?**: Yes

## Current Definition
```
An information content entity representing a verb phrase extracted from text.
```

## Instructions
[...rest of prompt...]
```

**Claude responds with iterations:**

```markdown
### Iteration 1

**GENERATE:**
"An information content entity that is about an occurrent as introduced 
in discourse, and which denotes the predicative content together with 
temporal and modal boundaries of that occurrent."

**CRITIQUE:**
- C1: ✓ - "verb phrase" not in definition
- C2: ✓ - genus is "information content entity"
- C3: ✓ - differentia specifies predicative content + boundaries
- C4: ✓ - defines what it IS
- I1: ✓ - "is about an occurrent"
- I2: ✓ - occurrent is BFO category
- I3: ✓ - "as introduced in discourse" present
- R1: ✓ - no epistemological terms
- R2: ✓ - uses "denotes" not "represents"
- R3: ✓ - no functional language
- R4: ✓ - no linguistic form references

Issues found: None

**VERIFY:** ✓ PASS

### Final Output

```turtle
:VerbPhrase
    a owl:Class ;
    rdfs:subClassOf cco:InformationContentEntity ;
    rdfs:label "Verb Phrase"@en ;
    skos:definition """An information content entity that is about an 
        occurrent as introduced in discourse, and which denotes the 
        predicative content together with temporal and modal boundaries 
        of that occurrent."""@en .
```
```

---

### Quick Start Workflow

```
1. Open your ontology file
2. Pick a class to improve
3. Copy the Master Prompt
4. Fill in the class information
5. Paste into Claude
6. Get back validated definition
7. Copy the Turtle output into your ontology
8. Repeat for next class
```

---

### Batch Mode (Simple Version)

For multiple classes, just list them all in one prompt:

```markdown
# Ralph Loop: Batch Definition Rewrite

Process these classes through the Ralph Loop. For each class, run 
Generate→Critique→Refine→Verify until PASS (max 5 iterations per class).

## Classes to Process

### Class 1
- IRI: :DocumentContent
- Parent: cco:DescriptiveInformationContentEntity
- Siblings: :RecordContent, :StatementContent
- Current: "Content from documents."

### Class 2
- IRI: :RecordContent
- Parent: cco:DescriptiveInformationContentEntity
- Siblings: :DocumentContent, :StatementContent
- Current: "Content from records."

### Class 3
- IRI: :StatementContent
- Parent: cco:DescriptiveInformationContentEntity
- Siblings: :DocumentContent, :RecordContent
- Current: "A statement."

## Additional Requirement
After processing all classes, verify that siblings are mutually exclusive 
(each definition clearly excludes the others).

## Output
For each class: Show iterations, then final Turtle block.
At end: Sibling exclusivity check results.
```

---

### Troubleshooting Common Failures

| Failure | Likely Cause | Fix |
|---------|--------------|-----|
| C1 fails repeatedly | Term is inherently self-referential | Use synonyms or describe function without naming |
| C3 fails | Can't distinguish from siblings | Ask: "What does THIS have that siblings don't?" |
| I1 fails | Unclear what ICE is about | Ask: "If I looked at the world, what would I point to?" |
| R1 present | Confusing creation with essence | Remove all mention of how it's found/made |
| Stuck after 5 iterations | Fundamental modeling issue | Stop and reconsider: Is this the right class? Right parent? |

---

### Cheat Sheet (Print This)

```
┌─────────────────────────────────────────────────────────────────┐
│                 RALPH LOOP CHEAT SHEET                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PATTERN FOR ICEs:                                              │
│  "A [parent] that is about [BFO entity] as introduced in       │
│   discourse, and which denotes [specific aspect]."             │
│                                                                 │
│  CHECKLIST:                                                     │
│  ✓ C1: Term not in definition                                  │
│  ✓ C2: Parent class named                                      │
│  ✓ C3: Differentia present                                     │
│  ✓ C4: What it IS (not how found)                              │
│  ✓ I1: "is about" present (ICEs)                               │
│  ✓ I2: BFO entity type (ICEs)                                  │
│  ✓ I3: "as introduced in discourse" (ICEs)                     │
│                                                                 │
│  RED FLAGS (auto-fail):                                         │
│  ✗ extracted/detected/identified/parsed                        │
│  ✗ represents (use "denotes")                                  │
│  ✗ serves to/functions to                                      │
│  ✗ noun phrase/verb phrase/encoded as                          │
│                                                                 │
│  LOOP: Generate → Critique → Refine → Verify                   │
│        Max 5 iterations, then escalate to human                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
