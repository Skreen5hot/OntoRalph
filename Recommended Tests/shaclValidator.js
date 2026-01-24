/**
 * @module shaclValidator
 * @description Validates CCO patterns aligned with expert-approved SHACL shapes
 *
 * Expert Review Status: ✅ APPROVED (2026-01-09)
 * Patterns are compliant with BFO/CCO standards per CCO/BFO Realist Ontologist review.
 *
 * Key BFO Principles Applied:
 * 1. The Realization Fallacy: Dispositions exist even if never realized
 * 2. Bearer Necessity: Roles cannot exist without bearers
 * 3. Open World vs Design: ICE can exist abstractly but concretization expected
 *
 * @see docs/ontograde/SHACL-VALIDATION-REVIEW.md
 * @see src/ontologies/ontograde-shapes.ttl
 */

import { isCCOClass, SUPPORTED_CCO_CLASSES } from '../../ontologies/cco-bfo-mapping.ttl.js';
import { BFO_LABELS } from '../../ontologies/bfo-core.ttl.js';
import { bfoValidator } from './bfoValidator.js';
import { isCCOIri, normalizeCCOIri, extractLocalPart, CCO_NAMESPACE_VARIANTS } from '../../ontologies/cco-iri-normalizer.js';
import { CCO_CLASS_SET, CCO_PREDICATE_SET, isValidCCOClass, isValidCCOPredicate, normalizeCCOTerm } from '../../ontologies/cco-classes.generated.js';

// CCO/BFO IRIs
const CCO = 'http://www.ontologyrepository.com/CommonCoreOntologies/';
const BFO = 'http://purl.obolibrary.org/obo/';
const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
const SUBCLASS_OF = 'http://www.w3.org/2000/01/rdf-schema#subClassOf';

// CCO Classes
const CCO_CLASSES = {
  InformationContentEntity: `${CCO}InformationContentEntity`,
  InformationBearingEntity: `${CCO}InformationBearingEntity`,
  DesignativeInformationContentEntity: `${CCO}DesignativeInformationContentEntity`,
  Role: `${CCO}Role`,
  Act: `${CCO}Act`,
  Agent: `${CCO}Agent`,
  TemporalInterval: `${CCO}TemporalInterval`,
  QualityMeasurement: `${CCO}QualityMeasurement`,
  MeasurementUnit: `${CCO}MeasurementUnit`,
};

// BFO Classes (for type validation)
const BFO_CLASSES = {
  IndependentContinuant: `${BFO}BFO_0000004`,
  Process: `${BFO}BFO_0000015`,
  Quality: `${BFO}BFO_0000019`,
};

// CCO Properties
const CCO_PROPS = {
  is_concretized_by: `${CCO}is_concretized_by`,
  concretizes: `${CCO}concretizes`,
  has_text_value: `${CCO}has_text_value`,
  is_bearer_of: `${CCO}is_bearer_of`,
  realizes: `${CCO}realizes`,
  designates: `${CCO}designates`,
  is_designated_by: `${CCO}is_designated_by`,
  participates_in: `${CCO}participates_in`,
  occurs_during: `${CCO}occurs_during`,
  has_start_time: `${CCO}has_start_time`,
  has_end_time: `${CCO}has_end_time`,
  has_measurement_value: `${CCO}has_measurement_value`,
  uses_measurement_unit: `${CCO}uses_measurement_unit`,
  is_measured_by: `${CCO}is_measured_by`,
  // EXPERT REVIEW (2026-01-13): Added "Realist Glue" properties per CCO expert
  is_part_of: `${CCO}is_part_of`,
  is_attribute_of: `${CCO}is_attribute_of`,
  affects: `${CCO}affects`,
  // EXPERT CERTIFICATION (2026-01-13): Additional predicates per CCO expert
  is_made_of: `${CCO}is_made_of`,
  is_site_of: `${CCO}is_site_of`,
};

/**
 * Domain/Range constraints for CCO predicates
 * Each predicate has:
 * - domain: Array of class IRIs that can be the subject
 * - range: Array of class IRIs that can be the object (or 'Literal' for datatype properties)
 * - description: Human-readable description for error messages
 *
 * Based on CCO documentation and BFO upper-level ontology
 * Note: These are simplified constraints suitable for Mermaid-level validation
 */
const PREDICATE_CONSTRAINTS = {
  [CCO_PROPS.is_concretized_by]: {
    domain: [`${CCO}InformationContentEntity`],
    range: [`${CCO}InformationBearingEntity`],
    description: 'ICE is_concretized_by IBE',
  },
  [CCO_PROPS.concretizes]: {
    domain: [`${CCO}InformationBearingEntity`],
    range: [`${CCO}InformationContentEntity`],
    description: 'IBE concretizes ICE',
  },
  [CCO_PROPS.has_text_value]: {
    domain: [`${CCO}InformationBearingEntity`],
    range: ['Literal'],
    description: 'IBE has_text_value Literal',
  },
  [CCO_PROPS.is_bearer_of]: {
    // IndependentContinuant or common CCO subtypes (Person, Agent, Organization, Artifact)
    domain: [`${BFO}BFO_0000004`, `${CCO}Person`, `${CCO}Agent`, `${CCO}Organization`, `${CCO}Artifact`],
    range: [`${CCO}Role`, `${CCO}StudentRole`, `${CCO}ResidentRole`, `${CCO}EmployeeRole`, `${BFO}BFO_0000023`], // Role and subtypes
    description: 'IndependentContinuant is_bearer_of Role',
  },
  [CCO_PROPS.realizes]: {
    // EXPERT REVIEW (2026-01-13): Domain rooted in bfo:Process (BFO_0000015) as cco:Act is a subtype
    domain: [`${BFO}BFO_0000015`, `${CCO}Act`, `${CCO}IntentionalAct`], // Process and subtypes
    range: [`${CCO}Role`, `${CCO}StudentRole`, `${CCO}ResidentRole`, `${CCO}EmployeeRole`, `${BFO}BFO_0000023`], // Role and subtypes
    description: 'Process realizes Role',
  },
  [CCO_PROPS.designates]: {
    domain: [`${CCO}DesignativeInformationContentEntity`, `${CCO}Name`, `${CCO}Identifier`],
    range: [], // Any entity can be designated
    description: 'DesignativeICE designates Entity',
  },
  [CCO_PROPS.is_designated_by]: {
    domain: [], // Any entity can be designated
    range: [`${CCO}DesignativeInformationContentEntity`, `${CCO}Name`, `${CCO}Identifier`],
    description: 'Entity is_designated_by DesignativeICE',
  },
  [CCO_PROPS.participates_in]: {
    domain: [`${CCO}Agent`, `${CCO}Person`, `${CCO}Organization`, `${BFO}BFO_0000040`], // Material entities
    range: [`${CCO}Act`, `${BFO}BFO_0000015`], // Process
    description: 'Agent participates_in Act',
  },
  [CCO_PROPS.occurs_during]: {
    domain: [`${CCO}Act`, `${BFO}BFO_0000015`], // Process
    range: [`${CCO}TemporalInterval`, `${BFO}BFO_0000038`], // Temporal region
    description: 'Act occurs_during TemporalInterval',
  },
  [CCO_PROPS.has_start_time]: {
    domain: [`${CCO}TemporalInterval`, `${BFO}BFO_0000038`],
    range: ['Literal'], // Datetime literal
    description: 'TemporalInterval has_start_time DateTime',
  },
  [CCO_PROPS.has_end_time]: {
    domain: [`${CCO}TemporalInterval`, `${BFO}BFO_0000038`],
    range: ['Literal'], // Datetime literal
    description: 'TemporalInterval has_end_time DateTime',
  },
  [CCO_PROPS.has_measurement_value]: {
    domain: [`${CCO}QualityMeasurement`],
    range: ['Literal'], // Numeric literal
    description: 'QualityMeasurement has_measurement_value Number',
  },
  [CCO_PROPS.uses_measurement_unit]: {
    domain: [`${CCO}QualityMeasurement`],
    range: [`${CCO}MeasurementUnit`],
    description: 'QualityMeasurement uses_measurement_unit MeasurementUnit',
  },
  [CCO_PROPS.is_measured_by]: {
    domain: [`${BFO}BFO_0000019`, `${CCO}Quality`], // Quality
    range: [`${CCO}QualityMeasurement`],
    description: 'Quality is_measured_by QualityMeasurement',
  },
  // EXPERT REVIEW (2026-01-13): Added "Realist Glue" properties per CCO expert
  // EXPERT CERTIFICATION (2026-01-13): is_part_of requires strict like-to-like checking
  // A Continuant can participate in a Process, but NEVER be a part of it.
  // Parts of processes must be other processes (temporal parts).
  [CCO_PROPS.is_part_of]: {
    // Strict like-to-like: Continuant to Continuant only, or Occurrent to Occurrent only
    // Cross-type relationships (Continuant part_of Occurrent) are VIOLATIONS
    domain: [`${BFO}BFO_0000002`, `${CCO}Person`, `${CCO}Organization`, `${CCO}Artifact`], // Continuants only
    range: [`${BFO}BFO_0000002`, `${CCO}Organization`, `${CCO}Artifact`, `${CCO}GroupOfAgents`], // Continuants only
    description: 'Continuant is_part_of Continuant (strict like-to-like)',
    // Note: Process parts handled separately via temporal part relations
    likeToLike: true, // Flag for special cross-category checking
  },
  [CCO_PROPS.is_attribute_of]: {
    // Qualities/Dispositions point to Independent Continuants
    domain: [`${BFO}BFO_0000019`, `${BFO}BFO_0000016`, `${CCO}Quality`, `${CCO}Disposition`], // Quality or Disposition
    range: [`${BFO}BFO_0000004`, `${CCO}Person`, `${CCO}Agent`, `${CCO}Organization`, `${CCO}Artifact`], // IndependentContinuant
    description: 'Quality/Disposition is_attribute_of IndependentContinuant',
  },
  [CCO_PROPS.affects]: {
    // Processes acting upon Material Entities
    domain: [`${BFO}BFO_0000015`, `${CCO}Act`, `${CCO}IntentionalAct`], // Process
    range: [`${BFO}BFO_0000040`, `${CCO}Person`, `${CCO}Agent`, `${CCO}Organization`, `${CCO}Artifact`], // MaterialEntity
    description: 'Process affects MaterialEntity',
  },
  // EXPERT CERTIFICATION (2026-01-13): Additional predicates per CCO expert
  [CCO_PROPS.is_made_of]: {
    // Relates an Artifact to a MaterialEntity (what it's composed of)
    domain: [`${CCO}Artifact`, `${BFO}BFO_0000030`], // Object (Artifact)
    range: [`${BFO}BFO_0000040`, `${CCO}Artifact`], // MaterialEntity
    description: 'Artifact is_made_of MaterialEntity',
  },
  [CCO_PROPS.is_site_of]: {
    // Relates a Site or Facility to a Process (spatial counterpart to occurs_during)
    domain: [`${CCO}Site`, `${CCO}Facility`, `${CCO}GeographicRegion`, `${BFO}BFO_0000029`], // Site
    range: [`${BFO}BFO_0000015`, `${CCO}Act`, `${CCO}IntentionalAct`], // Process
    description: 'Site is_site_of Process',
  },
};

// Known namespaces for vocabulary validation
// CCO has multiple valid namespace URIs depending on version/source
const KNOWN_NAMESPACES = {
  CCO: 'http://www.ontologyrepository.com/CommonCoreOntologies/',
  CCO_ALT: 'https://www.commoncoreontologies.org/',  // Alternative CCO namespace
  CCO_ALT_HTTP: 'http://www.commoncoreontologies.org/',  // HTTP variant
  BFO: 'http://purl.obolibrary.org/obo/',
  RDF: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  RDFS: 'http://www.w3.org/2000/01/rdf-schema#',
  OWL: 'http://www.w3.org/2002/07/owl#',
  XSD: 'http://www.w3.org/2001/XMLSchema#',
};

// Known predicates (CCO, RDF, RDFS properties we recognize)
const KNOWN_PREDICATES = new Set([
  // RDF/RDFS/OWL
  RDF_TYPE,
  SUBCLASS_OF,
  'http://www.w3.org/2000/01/rdf-schema#label',
  'http://www.w3.org/2000/01/rdf-schema#comment',
  'http://www.w3.org/2002/07/owl#sameAs',
  // CCO Properties
  ...Object.values(CCO_PROPS),
]);

// Known CCO class names (local part after namespace)
// Uses auto-generated CCO_CLASS_SET from cco-classes.generated.js
// Falls back to SUPPORTED_CCO_CLASSES for backwards compatibility
const KNOWN_CCO_CLASSES = CCO_CLASS_SET.size > 0 ? CCO_CLASS_SET : new Set(SUPPORTED_CCO_CLASSES);

// Known BFO class names (local part after namespace, e.g., "BFO_0000040")
const KNOWN_BFO_CLASSES = new Set(Object.keys(BFO_LABELS));

// Severity levels aligned with SHACL
const SEVERITY = {
  VIOLATION: 'violation', // Must be fixed - ontologically impossible otherwise
  WARNING: 'warning',     // Should be addressed - incomplete but valid
  INFO: 'info',           // Suggestion - nice to have
};

const subscribers = new Set();

/**
 * Notifies all subscribed listeners of an event.
 * @param {string} event - The name of the event.
 * @param {*} payload - The data associated with the event.
 */
function notify(event, payload) {
  for (const subscriber of subscribers) {
    subscriber(event, payload);
  }
}

export const shaclValidator = {
  state: {
    violations: [], // Array of pattern violations
    complianceScore: 0, // 0-100 percentage
    validationResults: new Map(), // diagramId -> result
  },

  actions: {
    /**
     * Validates CCO patterns in the RDF graph
     * @param {Object} params
     * @param {string} params.diagramId - Diagram identifier
     * @param {Store} params.rdfGraph - N3 Store with user's RDF triples
     */
    validatePatterns({ diagramId, rdfGraph }) {
      try {
        console.log(`[shaclValidator] Validating CCO patterns for diagram ${diagramId}...`);

        const result = shaclValidator.helpers.checkPatterns(rdfGraph);

        shaclValidator.state.violations = result.violations;
        shaclValidator.state.complianceScore = result.complianceScore;
        shaclValidator.state.validationResults.set(diagramId, result);

        console.log(`[shaclValidator] Pattern validation complete:`);
        console.log(`  - Total patterns checked: ${result.totalChecks}`);
        console.log(`  - Violations: ${result.violations.length}`);
        console.log(`  - Compliance score: ${result.complianceScore}%`);

        notify('patternsValidated', { diagramId, result });
      } catch (error) {
        console.error(`[shaclValidator] Validation failed:`, error);

        const errorResult = {
          pass: false,
          error: error.message,
          userMessage: shaclValidator.helpers.getUserFriendlyMessage(error),
        };

        shaclValidator.state.validationResults.set(diagramId, errorResult);
        notify('patternsValidationFailed', { diagramId, error: errorResult });
      }
    },
  },

  helpers: {
    /**
     * Checks all CCO patterns in the RDF graph
     * Patterns aligned with expert-approved SHACL shapes (2026-01-09)
     *
     * @param {Store} rdfGraph - N3 Store with user's RDF triples
     * @returns {Object} Validation result
     */
    checkPatterns(rdfGraph) {
      const issues = []; // violations and warnings
      const patternsChecked = [];

      // Pattern 1: Information Staircase (ICE/IBE)
      const staircaseResult = shaclValidator.helpers.checkInformationStaircase(rdfGraph);
      issues.push(...staircaseResult.issues);
      if (staircaseResult.entitiesChecked > 0) {
        patternsChecked.push('Information Staircase');
      }

      // Pattern 2: Role Pattern
      const roleResult = shaclValidator.helpers.checkRolePattern(rdfGraph);
      issues.push(...roleResult.issues);
      if (roleResult.entitiesChecked > 0) {
        patternsChecked.push('Role Pattern');
      }

      // Pattern 3: Designation Pattern
      const designationResult = shaclValidator.helpers.checkDesignationPattern(rdfGraph);
      issues.push(...designationResult.issues);
      if (designationResult.entitiesChecked > 0) {
        patternsChecked.push('Designation Pattern');
      }

      // Pattern 4: Temporal Interval Pattern
      const temporalResult = shaclValidator.helpers.checkTemporalIntervalPattern(rdfGraph);
      issues.push(...temporalResult.issues);
      if (temporalResult.entitiesChecked > 0) {
        patternsChecked.push('Temporal Interval Pattern');
      }

      // Pattern 5: Measurement Pattern
      const measurementResult = shaclValidator.helpers.checkMeasurementPattern(rdfGraph);
      issues.push(...measurementResult.issues);
      if (measurementResult.entitiesChecked > 0) {
        patternsChecked.push('Measurement Pattern');
      }

      // Pattern 10: Socio-Primal Pattern (Agent/Act)
      const socioPrimalResult = shaclValidator.helpers.checkSocioPrimalPattern(rdfGraph);
      issues.push(...socioPrimalResult.issues);
      if (socioPrimalResult.entitiesChecked > 0) {
        patternsChecked.push('Socio-Primal Pattern');
      }

      // Vocabulary Validation: Check for unrecognized entities and predicates
      const vocabularyResult = shaclValidator.helpers.checkVocabulary(rdfGraph);
      issues.push(...vocabularyResult.issues);
      if (vocabularyResult.entitiesChecked > 0 || vocabularyResult.predicatesChecked > 0) {
        patternsChecked.push('Vocabulary Validation');
      }

      // Calculate unknown percentage for display
      const totalEntities = vocabularyResult.entitiesChecked;
      const totalPredicates = vocabularyResult.predicatesChecked;
      const unknownEntities = vocabularyResult.unrecognizedEntityCount;
      const unknownPredicates = vocabularyResult.unrecognizedPredicateCount;

      // Domain/Range Validation: Check predicate constraints
      // Only run if vocabulary is mostly recognized (otherwise skip - can't validate unknown vocab)
      const recognizedRatio = totalEntities > 0 ? (totalEntities - unknownEntities) / totalEntities : 1;

      if (recognizedRatio >= 0.5) {
        // At least 50% recognized - domain/range validation is meaningful
        const domainRangeResult = shaclValidator.helpers.checkDomainRange(rdfGraph);
        issues.push(...domainRangeResult.issues);
        if (domainRangeResult.relationshipsChecked > 0) {
          patternsChecked.push('Domain/Range Validation');
        }
      }

      // Calculate unknown percentage including BOTH entities AND predicates
      const totalItems = totalEntities + totalPredicates;
      const unknownItems = unknownEntities + unknownPredicates;
      const unknownPercentage = totalItems > 0
        ? Math.round((unknownItems / totalItems) * 100)
        : 0;

      // Separate violations from warnings
      const violations = issues.filter(i => i.severity === SEVERITY.VIOLATION);
      const warnings = issues.filter(i => i.severity === SEVERITY.WARNING);
      const infos = issues.filter(i => i.severity === SEVERITY.INFO);

      // Pass/fail based on violations only (warnings don't fail validation)
      const pass = violations.length === 0;

      // Calculate compliance score
      // Violations: -1.0 each, Warnings: -0.3 each, Info: -0.1 each
      const maxScore = 100;
      const violationPenalty = violations.length * 10;
      const warningPenalty = warnings.length * 3;
      const infoPenalty = infos.length * 1;
      const complianceScore = Math.max(0, Math.round(maxScore - violationPenalty - warningPenalty - infoPenalty));

      // Determine if validation result should show "UNKNOWN" status
      // This happens when there are unrecognized entities/predicates
      const hasUnknownVocabulary = unknownEntities > 0 || unknownPredicates > 0;

      return {
        pass,
        violations: issues, // All issues for backwards compatibility
        violationCount: violations.length,
        warningCount: warnings.length,
        infoCount: infos.length,
        totalChecks: patternsChecked.length,
        patternsChecked,
        complianceScore,
        // NEW: Unknown vocabulary tracking
        vocabularyStatus: {
          totalEntities,
          totalPredicates,
          totalItems,
          unknownEntities,
          unknownPredicates,
          unknownItems,
          unknownPercentage,
          hasUnknownVocabulary,
          recognizedPercentage: totalItems > 0 ? 100 - unknownPercentage : 100,
        },
        message: hasUnknownVocabulary
          ? `${unknownPercentage}% unrecognized (${unknownEntities} entities, ${unknownPredicates} predicates)`
          : violations.length === 0 && warnings.length === 0
            ? 'All CCO patterns are valid'
            : violations.length > 0
              ? `Found ${violations.length} violation(s) and ${warnings.length} warning(s)`
              : `Found ${warnings.length} warning(s) - validation passed`,
      };
    },

    /**
     * Validates the Information Staircase pattern:
     * ICE → is_concretized_by → IBE → has_text_value → Literal
     *
     * EXPERT REVIEW (2026-01-09):
     * - ICE → is_concretized_by: WARNING (ICE can exist abstractly like a Law)
     * - IBE → concretizes: WARNING (blank slate IBE is rarely intended)
     * - IBE → has_text_value: WARNING (completes the staircase)
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkInformationStaircase(rdfGraph) {
      const issues = [];

      // Find all ICE entities (InformationContentEntity)
      const iceEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.InformationContentEntity
      );

      // Find all IBE entities (InformationBearingEntity)
      const ibeEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.InformationBearingEntity
      );

      // Check ICE entities
      for (const iceEntity of iceEntities) {
        const concretizationQuads = rdfGraph.getQuads(iceEntity, CCO_PROPS.is_concretized_by, null, null);

        if (concretizationQuads.length === 0) {
          // EXPERT: WARNING - ICE can exist abstractly (like a Law or Recipe)
          issues.push({
            pattern: 'Information Staircase',
            rule: 'ICE Concretization',
            severity: SEVERITY.WARNING,
            subject: iceEntity,
            message: `ICE ${shaclValidator.helpers.getShortIri(iceEntity)} should have an is_concretized_by relationship to an IBE`,
            explanation: 'While an ICE can exist abstractly (like a Law or Recipe), for practical modeling it should be concretized in a physical bearer.',
            fix: `Add: ${shaclValidator.helpers.getShortIri(iceEntity)} → is_concretized_by → [IBE]`,
          });
          continue;
        }

        // Check if target IBE has has_text_value
        for (const quad of concretizationQuads) {
          const ibeEntity = quad.object.value;
          const textValueQuads = rdfGraph.getQuads(ibeEntity, CCO_PROPS.has_text_value, null, null);

          if (textValueQuads.length === 0) {
            issues.push({
              pattern: 'Information Staircase',
              rule: 'IBE Text Value',
              severity: SEVERITY.WARNING,
              subject: ibeEntity,
              message: `IBE ${shaclValidator.helpers.getShortIri(ibeEntity)} should have a has_text_value relationship`,
              explanation: 'This completes the Information Staircase pattern from abstract information to concrete text.',
              fix: `Add: ${shaclValidator.helpers.getShortIri(ibeEntity)} → has_text_value → "value"`,
            });
          }
        }
      }

      // Check IBE entities for concretizes relationship (inverse check)
      for (const ibeEntity of ibeEntities) {
        const concretizesQuads = rdfGraph.getQuads(ibeEntity, CCO_PROPS.concretizes, null, null);
        const inverseConcretizesQuads = rdfGraph.getQuads(null, CCO_PROPS.is_concretized_by, ibeEntity, null);

        if (concretizesQuads.length === 0 && inverseConcretizesQuads.length === 0) {
          // EXPERT: WARNING - blank slate IBE is rarely intended
          issues.push({
            pattern: 'Information Staircase',
            rule: 'IBE Concretization',
            severity: SEVERITY.WARNING,
            subject: ibeEntity,
            message: `IBE ${shaclValidator.helpers.getShortIri(ibeEntity)} should concretize at least one ICE`,
            explanation: 'An IBE without information is a "blank slate" which is rarely the modeling intent.',
            fix: `Add: ${shaclValidator.helpers.getShortIri(ibeEntity)} → concretizes → [ICE]`,
          });
        }
      }

      return {
        issues,
        entitiesChecked: iceEntities.length + ibeEntities.length,
      };
    },

    /**
     * Validates the Role Pattern:
     * IndependentContinuant → is_bearer_of → Role (REQUIRED)
     * Process → realizes → Role (OPTIONAL)
     *
     * EXPERT REVIEW (2026-01-09):
     * - Bearer: VIOLATION - Role CANNOT exist without bearer (BFO principle)
     * - Realization: WARNING - Dispositions can remain dormant (BFO principle)
     * - Type validation: Bearer must be IndependentContinuant, Realizer must be Process
     *
     * BFO Principle: "A Disposition exists even if never realized. For example,
     * a 'Fire Extinguisher Role' exists even if the extinguisher never puts out
     * a fire. However, a Role CANNOT exist without a bearer."
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkRolePattern(rdfGraph) {
      const issues = [];

      // Find all Role entities
      const roleEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.Role
      );

      for (const roleEntity of roleEntities) {
        // Rule 1: Role MUST be borne by at least one entity (VIOLATION)
        const bearerQuads = rdfGraph.getQuads(null, CCO_PROPS.is_bearer_of, roleEntity, null);

        if (bearerQuads.length === 0) {
          // EXPERT: VIOLATION - Role cannot exist without bearer
          issues.push({
            pattern: 'Role Pattern',
            rule: 'Role Bearer',
            severity: SEVERITY.VIOLATION,
            subject: roleEntity,
            message: `Role ${shaclValidator.helpers.getShortIri(roleEntity)} must be borne by at least one entity`,
            explanation: 'In BFO, a Role (Disposition) cannot exist without a bearer - this is ontologically impossible.',
            fix: `Add: [Entity] → is_bearer_of → ${shaclValidator.helpers.getShortIri(roleEntity)}`,
          });
        } else {
          // Type validation: Bearer should be IndependentContinuant
          for (const quad of bearerQuads) {
            const bearerEntity = quad.subject.value;
            if (!shaclValidator.helpers.isInstanceOfBFOClass(rdfGraph, bearerEntity, BFO_CLASSES.IndependentContinuant)) {
              issues.push({
                pattern: 'Role Pattern',
                rule: 'Bearer Type',
                severity: SEVERITY.WARNING,
                subject: bearerEntity,
                message: `Bearer ${shaclValidator.helpers.getShortIri(bearerEntity)} should be an IndependentContinuant`,
                explanation: 'Only independent continuants (Person, Organization, Artifact, etc.) can bear roles per BFO.',
                fix: `Ensure ${shaclValidator.helpers.getShortIri(bearerEntity)} is typed as a subclass of bfo:IndependentContinuant`,
              });
            }
          }
        }

        // Rule 2: Role SHOULD be realized by at least one process (WARNING)
        const realizationQuads = rdfGraph.getQuads(null, CCO_PROPS.realizes, roleEntity, null);

        if (realizationQuads.length === 0) {
          // EXPERT: WARNING - Dispositions can remain dormant
          issues.push({
            pattern: 'Role Pattern',
            rule: 'Role Realization',
            severity: SEVERITY.WARNING,
            subject: roleEntity,
            message: `Role ${shaclValidator.helpers.getShortIri(roleEntity)} is not realized by any Process`,
            explanation: 'While dispositions can remain dormant (per BFO), consider adding a realizes relationship if this role has been actualized.',
            fix: `Add: [Process] → realizes → ${shaclValidator.helpers.getShortIri(roleEntity)}`,
          });
        } else {
          // Type validation: Realizer should be Process
          for (const quad of realizationQuads) {
            const realizerEntity = quad.subject.value;
            if (!shaclValidator.helpers.isInstanceOfBFOClass(rdfGraph, realizerEntity, BFO_CLASSES.Process)) {
              issues.push({
                pattern: 'Role Pattern',
                rule: 'Realizer Type',
                severity: SEVERITY.WARNING,
                subject: realizerEntity,
                message: `Realizer ${shaclValidator.helpers.getShortIri(realizerEntity)} should be a Process`,
                explanation: 'Only processes can realize roles per BFO.',
                fix: `Ensure ${shaclValidator.helpers.getShortIri(realizerEntity)} is typed as a subclass of bfo:Process`,
              });
            }
          }
        }
      }

      return {
        issues,
        entitiesChecked: roleEntities.length,
      };
    },

    /**
     * Validates the Designation Pattern:
     * DesignativeICE → designates → Entity (preferred)
     * OR Entity → is_designated_by → DesignativeICE
     *
     * EXPERT REVIEW (2026-01-09):
     * - VIOLATION: A "Name" that names nothing is not a Designative ICE
     *   in a realist sense; it's just an ICE (Information Content Entity)
     * - Either direction is acceptable for user flexibility
     * - `designates` is the preferred/encouraged direction
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkDesignationPattern(rdfGraph) {
      const issues = [];

      // Find all DesignativeInformationContentEntity instances
      const designativeEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.DesignativeInformationContentEntity
      );

      for (const designativeEntity of designativeEntities) {
        // Check if it designates something (preferred) OR something is designated by it
        const designatesQuads = rdfGraph.getQuads(designativeEntity, CCO_PROPS.designates, null, null);
        const designatedByQuads = rdfGraph.getQuads(null, CCO_PROPS.is_designated_by, designativeEntity, null);

        if (designatesQuads.length === 0 && designatedByQuads.length === 0) {
          // EXPERT: VIOLATION - Name that names nothing is not a name
          issues.push({
            pattern: 'Designation Pattern',
            rule: 'Designation Link',
            severity: SEVERITY.VIOLATION,
            subject: designativeEntity,
            message: `DesignativeICE ${shaclValidator.helpers.getShortIri(designativeEntity)} must designate an entity`,
            explanation: 'A "Name" that names nothing is not a Designative ICE in a realist sense - it\'s just an InformationContentEntity.',
            fix: `Add: ${shaclValidator.helpers.getShortIri(designativeEntity)} → designates → [Entity] (preferred) or [Entity] → is_designated_by → ${shaclValidator.helpers.getShortIri(designativeEntity)}`,
          });
        }
      }

      return {
        issues,
        entitiesChecked: designativeEntities.length,
      };
    },

    /**
     * Validates the Temporal Interval Pattern:
     * TemporalInterval → has_start_time → TemporalInstant (WARNING)
     * TemporalInterval → has_end_time → TemporalInstant (WARNING)
     * start_time <= end_time (VIOLATION if backwards)
     *
     * EXPERT REVIEW (2026-01-09):
     * - Start/End times: WARNING (ongoing processes may lack end time)
     * - Time ordering: VIOLATION (backwards time is impossible)
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkTemporalIntervalPattern(rdfGraph) {
      const issues = [];

      // Find all TemporalInterval entities
      const intervalEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.TemporalInterval
      );

      for (const intervalEntity of intervalEntities) {
        const startTimeQuads = rdfGraph.getQuads(intervalEntity, CCO_PROPS.has_start_time, null, null);
        const endTimeQuads = rdfGraph.getQuads(intervalEntity, CCO_PROPS.has_end_time, null, null);

        const hasStartTime = startTimeQuads.length > 0;
        const hasEndTime = endTimeQuads.length > 0;

        // Rule 1: Should have start time (WARNING)
        if (!hasStartTime) {
          issues.push({
            pattern: 'Temporal Interval Pattern',
            rule: 'Interval Start Time',
            severity: SEVERITY.WARNING,
            subject: intervalEntity,
            message: `TemporalInterval ${shaclValidator.helpers.getShortIri(intervalEntity)} should have a has_start_time relationship`,
            explanation: 'Use literal syntax: TI -->|has_start_time| "2026-01-01T00:00:00"',
            fix: `Add: ${shaclValidator.helpers.getShortIri(intervalEntity)} -->|has_start_time| "YYYY-MM-DDTHH:MM:SS"`,
          });
        }

        // Rule 2: Should have end time (WARNING)
        if (!hasEndTime) {
          issues.push({
            pattern: 'Temporal Interval Pattern',
            rule: 'Interval End Time',
            severity: SEVERITY.WARNING,
            subject: intervalEntity,
            message: `TemporalInterval ${shaclValidator.helpers.getShortIri(intervalEntity)} should have a has_end_time relationship`,
            explanation: 'Use literal syntax: TI -->|has_end_time| "2026-12-31T23:59:59"',
            fix: `Add: ${shaclValidator.helpers.getShortIri(intervalEntity)} -->|has_end_time| "YYYY-MM-DDTHH:MM:SS"`,
          });
        }

        // Rule 3: Start time must be <= end time (VIOLATION if backwards)
        if (hasStartTime && hasEndTime) {
          const startValue = shaclValidator.helpers.extractTimeValue(startTimeQuads[0].object);
          const endValue = shaclValidator.helpers.extractTimeValue(endTimeQuads[0].object);

          if (startValue && endValue && startValue > endValue) {
            issues.push({
              pattern: 'Temporal Interval Pattern',
              rule: 'Time Ordering',
              severity: SEVERITY.VIOLATION,
              subject: intervalEntity,
              message: `TemporalInterval ${shaclValidator.helpers.getShortIri(intervalEntity)} has end time before start time`,
              explanation: 'Backwards time intervals are logically/ontologically impossible.',
              fix: 'Swap the start and end time values or correct the timestamps',
            });
          }
        }
      }

      return {
        issues,
        entitiesChecked: intervalEntities.length,
      };
    },

    /**
     * Validates the Measurement Pattern:
     * Quality → is_measured_by → QualityMeasurement (VIOLATION)
     * QualityMeasurement → has_measurement_value → xsd:decimal (VIOLATION)
     * QualityMeasurement → uses_measurement_unit → MeasurementUnit (VIOLATION)
     *
     * EXPERT REVIEW (2026-01-09):
     * - All three components (Value, Unit, Quality) are REQUIRED
     * - Severity: VIOLATION for all rules
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkMeasurementPattern(rdfGraph) {
      const issues = [];

      // Find all QualityMeasurement entities
      const measurementEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.QualityMeasurement
      );

      for (const measurementEntity of measurementEntities) {
        // Rule 1: Must be linked to a Quality (via inverse is_measured_by)
        const qualityQuads = rdfGraph.getQuads(null, CCO_PROPS.is_measured_by, measurementEntity, null);

        if (qualityQuads.length === 0) {
          issues.push({
            pattern: 'Measurement Pattern',
            rule: 'Measurement Target',
            severity: SEVERITY.VIOLATION,
            subject: measurementEntity,
            message: `QualityMeasurement ${shaclValidator.helpers.getShortIri(measurementEntity)} must be linked to a Quality`,
            explanation: 'A measurement without a target quality is meaningless.',
            fix: `Add: [Quality] → is_measured_by → ${shaclValidator.helpers.getShortIri(measurementEntity)}`,
          });
        }

        // Rule 2: Must have a numeric value
        const valueQuads = rdfGraph.getQuads(measurementEntity, CCO_PROPS.has_measurement_value, null, null);

        if (valueQuads.length === 0) {
          issues.push({
            pattern: 'Measurement Pattern',
            rule: 'Measurement Value',
            severity: SEVERITY.VIOLATION,
            subject: measurementEntity,
            message: `QualityMeasurement ${shaclValidator.helpers.getShortIri(measurementEntity)} must have a measurement value`,
            explanation: 'A measurement without a value is incomplete.',
            fix: `Add: ${shaclValidator.helpers.getShortIri(measurementEntity)} → has_measurement_value → [numeric literal]`,
          });
        }

        // Rule 3: Must have a unit
        const unitQuads = rdfGraph.getQuads(measurementEntity, CCO_PROPS.uses_measurement_unit, null, null);

        if (unitQuads.length === 0) {
          issues.push({
            pattern: 'Measurement Pattern',
            rule: 'Measurement Unit',
            severity: SEVERITY.VIOLATION,
            subject: measurementEntity,
            message: `QualityMeasurement ${shaclValidator.helpers.getShortIri(measurementEntity)} must specify a measurement unit`,
            explanation: 'A numeric value without a unit is ambiguous (is "5" meters, kilograms, or something else?).',
            fix: `Add: ${shaclValidator.helpers.getShortIri(measurementEntity)} → uses_measurement_unit → [MeasurementUnit]`,
          });
        }
      }

      return {
        issues,
        entitiesChecked: measurementEntities.length,
      };
    },

    /**
     * Validates the Socio-Primal Pattern:
     * Agent → participates_in → Act (INFO)
     * Act → occurs_during → TemporalInterval (WARNING)
     * Act should have at least one participant Agent (WARNING)
     *
     * EXPERT REVIEW (2026-01-09):
     * - This pattern was identified as MISSING from original set
     * - Critical for modeling agent participation in temporal activities
     * - "In CCO, social reality is captured through the participation of
     *    Agents in Acts that occupy a specific Temporal Interval."
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number }
     */
    checkSocioPrimalPattern(rdfGraph) {
      const issues = [];

      // Find all Act entities
      const actEntities = shaclValidator.helpers.findEntitiesOfType(
        rdfGraph,
        CCO_CLASSES.Act
      );

      for (const actEntity of actEntities) {
        // Rule 1: Act should occur during a TemporalInterval (WARNING)
        const temporalQuads = rdfGraph.getQuads(actEntity, CCO_PROPS.occurs_during, null, null);

        if (temporalQuads.length === 0) {
          issues.push({
            pattern: 'Socio-Primal Pattern',
            rule: 'Act Temporal Grounding',
            severity: SEVERITY.WARNING,
            subject: actEntity,
            message: `Act ${shaclValidator.helpers.getShortIri(actEntity)} should have an occurs_during relationship`,
            explanation: 'Temporal grounding helps establish when the act took place.',
            fix: `Add: ${shaclValidator.helpers.getShortIri(actEntity)} → occurs_during → [TemporalInterval]`,
          });
        }

        // Rule 2: Act should have at least one participant (WARNING)
        const participantQuads = rdfGraph.getQuads(null, CCO_PROPS.participates_in, actEntity, null);

        if (participantQuads.length === 0) {
          issues.push({
            pattern: 'Socio-Primal Pattern',
            rule: 'Act Participant',
            severity: SEVERITY.WARNING,
            subject: actEntity,
            message: `Act ${shaclValidator.helpers.getShortIri(actEntity)} should have at least one Agent participant`,
            explanation: 'Acts without participants are abstract descriptions.',
            fix: `Add: [Agent] → participates_in → ${shaclValidator.helpers.getShortIri(actEntity)}`,
          });
        }
      }

      return {
        issues,
        entitiesChecked: actEntities.length,
      };
    },

    /**
     * Validates Domain/Range constraints for CCO predicates
     *
     * This is appropriate for Mermaid because:
     * - Users draw relationships between nodes (subject --predicate--> object)
     * - CCO defines which types can be connected by which predicates
     * - This catches semantic errors like "Person --realizes--> House"
     *
     * Approach:
     * - Only validates predicates with known constraints (CCO predicates)
     * - Checks if subject type is compatible with domain
     * - Checks if object type is compatible with range
     * - Uses INFO severity (not VIOLATION) since type inference is limited
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, relationshipsChecked: number }
     */
    checkDomainRange(rdfGraph) {
      const issues = [];
      let relationshipsChecked = 0;

      // Get all quads with CCO predicates that have constraints
      const allQuads = rdfGraph.getQuads(null, null, null, null);

      for (const quad of allQuads) {
        const predicateIri = quad.predicate.value;
        const constraint = PREDICATE_CONSTRAINTS[predicateIri];

        // Skip predicates without constraints (rdf:type, rdfs:subClassOf, etc.)
        if (!constraint) continue;

        relationshipsChecked++;

        const subjectIri = quad.subject.value;
        const objectIri = quad.object.termType === 'NamedNode' ? quad.object.value : null;
        const objectIsLiteral = quad.object.termType === 'Literal';

        // Get types of subject
        const subjectTypes = shaclValidator.helpers.getEntityTypes(rdfGraph, subjectIri);

        // Check domain constraint (if not empty - empty means "any")
        if (constraint.domain.length > 0) {
          const domainValid = shaclValidator.helpers.isTypeCompatible(
            rdfGraph,
            subjectTypes,
            constraint.domain
          );

          if (!domainValid && subjectTypes.length > 0) {
            const subjectTypeName = shaclValidator.helpers.getShortIri(subjectTypes[0]);
            const expectedDomain = constraint.domain
              .map(d => shaclValidator.helpers.getShortIri(d))
              .join(' or ');
            const predicateName = shaclValidator.helpers.getPredicateName(predicateIri);

            issues.push({
              pattern: 'Domain/Range Validation',
              rule: 'Domain Constraint',
              severity: SEVERITY.WARNING,
              subject: subjectIri,
              message: `"${predicateName}" expects subject of type ${expectedDomain}, but found ${subjectTypeName}`,
              explanation: `The predicate "${predicateName}" is designed for ${constraint.description}. ` +
                `Using it with ${subjectTypeName} may be semantically incorrect.`,
              fix: `Either change the subject to a ${expectedDomain}, or use a different predicate`,
            });
          }
        }

        // Check range constraint
        if (constraint.range.length > 0) {
          // Check if range expects Literal
          if (constraint.range.includes('Literal')) {
            if (!objectIsLiteral) {
              const predicateName = shaclValidator.helpers.getPredicateName(predicateIri);
              issues.push({
                pattern: 'Domain/Range Validation',
                rule: 'Range Constraint',
                severity: SEVERITY.WARNING,
                subject: objectIri || quad.object.value,
                message: `"${predicateName}" expects a literal value, but found a named node`,
                explanation: `The predicate "${predicateName}" should point to a literal value (text, number, date), ` +
                  `not another entity.`,
                fix: `Use a literal value like "text" or "123" instead of an entity reference`,
              });
            }
          } else if (objectIri) {
            // Range expects a specific type
            const objectTypes = shaclValidator.helpers.getEntityTypes(rdfGraph, objectIri);
            const rangeValid = shaclValidator.helpers.isTypeCompatible(
              rdfGraph,
              objectTypes,
              constraint.range
            );

            if (!rangeValid && objectTypes.length > 0) {
              const objectTypeName = shaclValidator.helpers.getShortIri(objectTypes[0]);
              const expectedRange = constraint.range
                .map(r => shaclValidator.helpers.getShortIri(r))
                .join(' or ');
              const predicateName = shaclValidator.helpers.getPredicateName(predicateIri);

              issues.push({
                pattern: 'Domain/Range Validation',
                rule: 'Range Constraint',
                severity: SEVERITY.WARNING,
                subject: objectIri,
                message: `"${predicateName}" expects object of type ${expectedRange}, but found ${objectTypeName}`,
                explanation: `The predicate "${predicateName}" is designed for ${constraint.description}. ` +
                  `Using it with ${objectTypeName} may be semantically incorrect.`,
                fix: `Either change the object to a ${expectedRange}, or use a different predicate`,
              });
            }
          }
        }
      }

      return {
        issues,
        relationshipsChecked,
      };
    },

    /**
     * Gets the types of an entity from the RDF graph
     * @param {Store} rdfGraph - N3 Store
     * @param {string} entityIri - Entity IRI
     * @returns {Array<string>} Array of type IRIs
     */
    getEntityTypes(rdfGraph, entityIri) {
      const typeQuads = rdfGraph.getQuads(entityIri, RDF_TYPE, null, null);
      return typeQuads.map(q => q.object.value);
    },

    /**
     * Checks if any of the entity's types are compatible with the constraint types
     * Compatible means: exact match OR subclass of constraint type
     *
     * @param {Store} rdfGraph - N3 Store
     * @param {Array<string>} entityTypes - Types of the entity
     * @param {Array<string>} constraintTypes - Types allowed by constraint
     * @returns {boolean} True if compatible
     */
    isTypeCompatible(rdfGraph, entityTypes, constraintTypes) {
      if (entityTypes.length === 0) {
        // No type info - can't validate, assume OK
        return true;
      }

      for (const entityType of entityTypes) {
        // Check exact match
        if (constraintTypes.includes(entityType)) {
          return true;
        }

        // Check if entity type is a subclass of any constraint type
        for (const constraintType of constraintTypes) {
          if (shaclValidator.helpers.isSubclassOf(rdfGraph, entityType, constraintType)) {
            return true;
          }
        }
      }

      return false;
    },

    /**
     * Checks if classA is a subclass of classB (directly or transitively)
     * Uses the subclass relationships in BOTH the user's RDF graph AND the
     * CCO/BFO reference ontology (from bfoValidator.state.referenceStore)
     *
     * @param {Store} rdfGraph - N3 Store (user's graph)
     * @param {string} classA - Potential subclass
     * @param {string} classB - Potential superclass
     * @returns {boolean} True if classA is subclass of classB
     */
    isSubclassOf(rdfGraph, classA, classB) {
      const visited = new Set();
      const queue = [classA];

      // Get reference store if available (contains CCO/BFO subclass hierarchy)
      const referenceStore = bfoValidator.state.referenceStore;

      while (queue.length > 0) {
        const current = queue.shift();
        if (visited.has(current)) continue;
        visited.add(current);

        if (current === classB) return true;

        // Get superclasses from user's graph
        const userSuperclassQuads = rdfGraph.getQuads(current, SUBCLASS_OF, null, null);
        for (const quad of userSuperclassQuads) {
          queue.push(quad.object.value);
        }

        // Also get superclasses from reference ontology (CCO/BFO hierarchy)
        if (referenceStore) {
          const refSuperclassQuads = referenceStore.getQuads(current, SUBCLASS_OF, null, null);
          for (const quad of refSuperclassQuads) {
            // Skip blank nodes
            if (!quad.object.value.startsWith('_:')) {
              queue.push(quad.object.value);
            }
          }
        }
      }

      return false;
    },

    /**
     * Gets a human-readable predicate name from a full IRI
     * @param {string} predicateIri - Full predicate IRI
     * @returns {string} Human-readable name (e.g., "is_bearer_of")
     */
    getPredicateName(predicateIri) {
      const lastSlash = predicateIri.lastIndexOf('/');
      const lastHash = predicateIri.lastIndexOf('#');
      const splitIndex = Math.max(lastSlash, lastHash);
      if (splitIndex > 0) {
        return predicateIri.substring(splitIndex + 1);
      }
      return predicateIri;
    },

    /**
     * Validates vocabulary usage in the RDF graph
     * Checks for:
     * 1. Classes that don't exist in CCO or BFO (validates class names, not just namespaces)
     * 2. Predicates not in the known CCO/RDF/RDFS vocabulary
     *
     * This helps users catch:
     * - Misspelled class names (e.g., "Persosn" instead of "Person")
     * - Invalid namespace prefixes (e.g., "foo:RestRole")
     * - Custom predicates that may not be recognized
     *
     * @param {Store} rdfGraph - N3 Store
     * @returns {Object} { issues: Array, entitiesChecked: number, predicatesChecked: number }
     */
    checkVocabulary(rdfGraph) {
      const issues = [];
      const checkedEntities = new Set();
      const checkedPredicates = new Set();
      const unrecognizedEntities = new Set();
      const unrecognizedPredicates = new Set();

      // Get all quads in the graph
      const allQuads = rdfGraph.getQuads(null, null, null, null);

      for (const quad of allQuads) {
        // Check subject (entity)
        if (quad.subject.termType === 'NamedNode') {
          const subjectIri = quad.subject.value;
          if (!checkedEntities.has(subjectIri)) {
            checkedEntities.add(subjectIri);
            if (!shaclValidator.helpers.isKnownEntity(subjectIri)) {
              unrecognizedEntities.add(subjectIri);
            }
          }
        }

        // Check predicate
        const predicateIri = quad.predicate.value;
        if (!checkedPredicates.has(predicateIri)) {
          checkedPredicates.add(predicateIri);
          if (!KNOWN_PREDICATES.has(predicateIri) &&
              !shaclValidator.helpers.isKnownPredicate(predicateIri) &&
              !shaclValidator.helpers.isKnownNamespace(predicateIri)) {
            unrecognizedPredicates.add(predicateIri);
          }
        }

        // Check object (if it's a named node, not a literal)
        if (quad.object.termType === 'NamedNode') {
          const objectIri = quad.object.value;
          if (!checkedEntities.has(objectIri)) {
            checkedEntities.add(objectIri);
            if (!shaclValidator.helpers.isKnownEntity(objectIri)) {
              unrecognizedEntities.add(objectIri);
            }
          }
        }
      }

      // Create WARNING messages for unrecognized entities
      // EXPERT REVIEW (2026-01-13): Elevated from INFO to WARNING per CCO expert.
      // A typo like "cco:Persosn" represents a failure to ground the model in CCO's semantic space.
      for (const entityIri of unrecognizedEntities) {
        const classInfo = shaclValidator.helpers.getClassValidationInfo(entityIri);
        issues.push({
          pattern: 'Vocabulary Validation',
          rule: classInfo.rule,
          severity: SEVERITY.WARNING,
          subject: entityIri,
          message: classInfo.message,
          explanation: classInfo.explanation,
          fix: classInfo.fix,
        });
      }

      // Create WARNING messages for unrecognized predicates
      // EXPERT REVIEW (2026-01-13): Elevated from INFO to WARNING per CCO expert.
      for (const predicateIri of unrecognizedPredicates) {
        issues.push({
          pattern: 'Vocabulary Validation',
          rule: 'Unknown Predicate',
          severity: SEVERITY.WARNING,
          subject: predicateIri,
          message: `Predicate "${shaclValidator.helpers.getDisplayIri(predicateIri)}" is not a recognized CCO/BFO/RDF property`,
          explanation: 'This predicate is not in the list of known CCO, BFO, RDF, or RDFS properties. ' +
            'It may be a custom property, a typo, or from a namespace not yet supported. ' +
            'Pattern validation may not work correctly for relationships using this predicate.',
          fix: `If this is intentional, you can ignore this message. Otherwise, use a recognized CCO predicate ` +
            `(e.g., "is_bearer_of", "realizes", "concretizes", "designates")`,
        });
      }

      return {
        issues,
        entitiesChecked: checkedEntities.size,
        predicatesChecked: checkedPredicates.size,
        unrecognizedEntityCount: unrecognizedEntities.size,
        unrecognizedPredicateCount: unrecognizedPredicates.size,
      };
    },

    /**
     * Checks if an IRI belongs to a known namespace
     * Supports all CCO IRI variants
     * @param {string} iri - The IRI to check
     * @returns {boolean} True if IRI is in a known namespace
     */
    isKnownNamespace(iri) {
      // Check CCO namespace variants (from normalizer)
      if (isCCOIri(iri)) {
        return true;
      }

      // Check other known namespaces
      for (const namespace of Object.values(KNOWN_NAMESPACES)) {
        if (iri.startsWith(namespace)) {
          return true;
        }
      }
      // Also allow example.org for testing purposes
      if (iri.startsWith('http://example.org/') || iri.startsWith('https://example.org/')) {
        return true;
      }
      return false;
    },

    /**
     * Checks if an entity IRI is a known CCO or BFO class
     * Validates BOTH namespace AND class name
     * Supports all CCO IRI variants including numeric IDs (ont#####)
     * @param {string} iri - The IRI to check
     * @returns {boolean} True if IRI is a known entity
     */
    isKnownEntity(iri) {
      // Allow example.org for testing (instance IRIs)
      if (iri.startsWith('http://example.org/') || iri.startsWith('https://example.org/')) {
        return true;
      }

      // Check if it's any CCO IRI variant (including numeric IDs)
      if (isCCOIri(iri)) {
        // Extract the local part
        const localPart = extractLocalPart(iri);
        if (!localPart) return false;

        // Check directly against generated class set (includes numeric IDs)
        if (KNOWN_CCO_CLASSES.has(localPart)) return true;

        // Also check normalized form (converts ont##### to class name)
        const normalized = normalizeCCOTerm(localPart);
        if (KNOWN_CCO_CLASSES.has(normalized)) return true;

        return false;
      }

      // Extract namespace and local part for non-CCO IRIs
      const parsed = shaclValidator.helpers.parseIri(iri);
      if (!parsed) return false;

      const { namespace, localPart } = parsed;

      // Check BFO namespace
      if (namespace === KNOWN_NAMESPACES.BFO) {
        return KNOWN_BFO_CLASSES.has(localPart);
      }

      // Check RDF/RDFS/OWL namespaces (always valid)
      if (namespace === KNOWN_NAMESPACES.RDF ||
          namespace === KNOWN_NAMESPACES.RDFS ||
          namespace === KNOWN_NAMESPACES.OWL ||
          namespace === KNOWN_NAMESPACES.XSD) {
        return true;
      }

      // Unknown namespace
      return false;
    },

    /**
     * Checks if a predicate IRI is a known CCO predicate
     * Uses auto-generated CCO_PREDICATE_SET from cco-classes.generated.js
     * @param {string} iri - The predicate IRI to check
     * @returns {boolean} True if IRI is a known CCO predicate
     */
    isKnownPredicate(iri) {
      // Check if it's a CCO IRI
      if (isCCOIri(iri)) {
        const localPart = extractLocalPart(iri);
        if (!localPart) return false;

        // Check against generated predicate set
        if (CCO_PREDICATE_SET.has(localPart)) return true;

        // Also try normalizing (for numeric IDs)
        const normalized = normalizeCCOTerm(localPart);
        if (CCO_PREDICATE_SET.has(normalized)) return true;
      }

      return false;
    },

    /**
     * Parses an IRI into namespace and local part
     * @param {string} iri - Full IRI
     * @returns {Object|null} { namespace, localPart } or null if not parseable
     */
    parseIri(iri) {
      if (!iri.includes('://')) return null;

      const hashIndex = iri.lastIndexOf('#');
      const slashIndex = iri.lastIndexOf('/');
      const splitIndex = Math.max(hashIndex, slashIndex);

      if (splitIndex > 0 && splitIndex < iri.length - 1) {
        return {
          namespace: iri.substring(0, splitIndex + 1),
          localPart: iri.substring(splitIndex + 1),
        };
      }
      return null;
    },

    /**
     * Gets detailed validation info for an unrecognized entity
     * @param {string} iri - The unrecognized IRI
     * @returns {Object} { rule, message, explanation, fix }
     */
    getClassValidationInfo(iri) {
      const parsed = shaclValidator.helpers.parseIri(iri);

      if (!parsed) {
        return {
          rule: 'Invalid IRI',
          message: `"${iri}" is not a valid IRI format`,
          explanation: 'The IRI could not be parsed. It should be a full URL like http://example.org/ClassName.',
          fix: 'Use a valid IRI format (e.g., "http://www.ontologyrepository.com/CommonCoreOntologies/Person")',
        };
      }

      const { namespace, localPart } = parsed;

      // Check if namespace is CCO but class doesn't exist
      if (namespace === KNOWN_NAMESPACES.CCO ||
          namespace === KNOWN_NAMESPACES.CCO_ALT ||
          namespace === KNOWN_NAMESPACES.CCO_ALT_HTTP) {
        return {
          rule: 'Unknown CCO Class',
          message: `Class "cco:${localPart}" does not exist in CCO vocabulary`,
          explanation: `"${localPart}" is not a recognized CCO class. ` +
            'This may be a typo (e.g., "Persosn" instead of "Person") or a class not yet supported. ' +
            `Known CCO classes include: ${Array.from(KNOWN_CCO_CLASSES).slice(0, 5).join(', ')}, etc.`,
          fix: `Check spelling of "${localPart}" or use a valid CCO class like Person, Role, Agent, Organization, etc.`,
        };
      }

      // Check if namespace is BFO but class doesn't exist
      if (namespace === KNOWN_NAMESPACES.BFO) {
        return {
          rule: 'Unknown BFO Class',
          message: `Class "bfo:${localPart}" does not exist in BFO vocabulary`,
          explanation: `"${localPart}" is not a recognized BFO class. ` +
            'BFO classes use the format BFO_XXXXXXX (e.g., BFO_0000040 for Material Entity). ' +
            `Known BFO classes include: ${Array.from(KNOWN_BFO_CLASSES).slice(0, 5).join(', ')}, etc.`,
          fix: `Use a valid BFO class ID (e.g., BFO_0000040, BFO_0000023, BFO_0000015)`,
        };
      }

      // Unknown namespace entirely
      return {
        rule: 'Unrecognized Namespace',
        message: `Entity "${shaclValidator.helpers.getDisplayIri(iri)}" is not using a recognized CCO/BFO namespace`,
        explanation: `This IRI uses namespace "${namespace}" which is not CCO or BFO. ` +
          'The entity will not be validated against CCO patterns.',
        fix: `Use CCO namespace (${KNOWN_NAMESPACES.CCO}) or BFO namespace (${KNOWN_NAMESPACES.BFO})`,
      };
    },

    /**
     * Gets a display-friendly version of an IRI
     * Shows the full IRI for unrecognized namespaces, short form for known ones
     * @param {string} iri - Full IRI
     * @returns {string} Display-friendly IRI
     */
    getDisplayIri(iri) {
      // For short IRIs that look like prefixed names (e.g., "foo:Bar"), show as-is
      if (!iri.includes('://')) {
        return iri;
      }
      // For full IRIs, show the last part after / or #
      const hashIndex = iri.lastIndexOf('#');
      const slashIndex = iri.lastIndexOf('/');
      const splitIndex = Math.max(hashIndex, slashIndex);
      if (splitIndex > 0 && splitIndex < iri.length - 1) {
        const localPart = iri.substring(splitIndex + 1);
        const prefix = iri.substring(0, splitIndex + 1);
        // If it's a known namespace, use short form
        if (prefix === KNOWN_NAMESPACES.CCO ||
            prefix === KNOWN_NAMESPACES.CCO_ALT ||
            prefix === KNOWN_NAMESPACES.CCO_ALT_HTTP) return `cco:${localPart}`;
        if (prefix === KNOWN_NAMESPACES.BFO) return `bfo:${localPart}`;
        if (prefix === KNOWN_NAMESPACES.RDF) return `rdf:${localPart}`;
        if (prefix === KNOWN_NAMESPACES.RDFS) return `rdfs:${localPart}`;
        // For unknown namespaces, show the full IRI
        return iri;
      }
      return iri;
    },

    /**
     * Extracts a time value from an RDF object for comparison
     * @param {Object} rdfObject - N3 term (NamedNode or Literal)
     * @returns {Date|null} Parsed date or null if not a date
     */
    extractTimeValue(rdfObject) {
      if (!rdfObject) return null;

      // If it's a literal with date/time value
      if (rdfObject.termType === 'Literal') {
        const value = rdfObject.value;
        // Try parsing as ISO date
        const dateMatch = value.match(/\d{4}-\d{2}-\d{2}/);
        if (dateMatch) {
          return new Date(dateMatch[0]);
        }
        // Try parsing as timestamp
        const parsed = Date.parse(value);
        if (!isNaN(parsed)) {
          return new Date(parsed);
        }
      }

      return null;
    },

    /**
     * Checks if an entity is an instance of a BFO class (or subclass)
     * This is a simplified check - full reasoning would require OWL reasoner
     *
     * @param {Store} rdfGraph - N3 Store
     * @param {string} entityIri - Entity IRI to check
     * @param {string} bfoClassIri - BFO class IRI
     * @returns {boolean} True if entity is typed as the BFO class
     */
    isInstanceOfBFOClass(rdfGraph, entityIri, bfoClassIri) {
      // Check direct type
      const typeQuads = rdfGraph.getQuads(entityIri, RDF_TYPE, bfoClassIri, null);
      if (typeQuads.length > 0) return true;

      // Check if entity's type is a subclass of the BFO class
      const entityTypes = rdfGraph.getQuads(entityIri, RDF_TYPE, null, null);
      for (const typeQuad of entityTypes) {
        const entityType = typeQuad.object.value;
        const subclassQuads = rdfGraph.getQuads(entityType, SUBCLASS_OF, bfoClassIri, null);
        if (subclassQuads.length > 0) return true;
      }

      // For simplicity, we don't fail type checks if we can't determine type
      // This allows users to model without full BFO typing
      // Return true to avoid false positives when type info is missing
      const hasAnyType = rdfGraph.getQuads(entityIri, RDF_TYPE, null, null).length > 0;
      if (!hasAnyType) return true; // No type info - don't penalize

      return false;
    },

    /**
     * Finds all entities of a given type (including subclasses)
     * @param {Store} rdfGraph - N3 Store
     * @param {string} typeIri - Class IRI to search for
     * @returns {Array<string>} Array of entity IRIs
     */
    findEntitiesOfType(rdfGraph, typeIri) {
      const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
      const SUBCLASS_OF = 'http://www.w3.org/2000/01/rdf-schema#subClassOf';
      const entities = new Set();

      // Direct instances
      const directInstances = rdfGraph.getQuads(null, RDF_TYPE, typeIri, null);
      for (const quad of directInstances) {
        entities.add(quad.subject.value);
      }

      // Instances of subclasses
      const subclassQuads = rdfGraph.getQuads(null, SUBCLASS_OF, typeIri, null);
      for (const subclassQuad of subclassQuads) {
        const subclass = subclassQuad.subject.value;
        const subclassInstances = rdfGraph.getQuads(null, RDF_TYPE, subclass, null);
        for (const quad of subclassInstances) {
          entities.add(quad.subject.value);
        }
      }

      return Array.from(entities);
    },

    /**
     * Gets a short form of an IRI for display
     * @param {string} iri - Full IRI
     * @returns {string} Short form (e.g., "cco:Person")
     */
    getShortIri(iri) {
      if (iri.includes('CommonCoreOntologies/')) {
        const parts = iri.split('/');
        return `cco:${parts[parts.length - 1]}`;
      }
      if (iri.includes('purl.obolibrary.org/obo/')) {
        const parts = iri.split('/');
        return `bfo:${parts[parts.length - 1]}`;
      }
      if (iri.includes('example.org/')) {
        const parts = iri.split('/');
        return `ex:${parts[parts.length - 1]}`;
      }
      return iri;
    },

    /**
     * Returns user-friendly error messages
     * @param {Error} error - Error object
     * @returns {string} User-friendly message
     */
    getUserFriendlyMessage(error) {
      if (error.message.includes('not initialized')) {
        return 'Pattern validator is not ready. Please try again.';
      }

      return 'An error occurred during pattern validation. Please check your diagram syntax.';
    },
  },

  subscribe(fn) {
    subscribers.add(fn);
  },

  unsubscribe(fn) {
    subscribers.delete(fn);
  },

  notify, // Expose for testing
};
