import { EventEmitter } from 'node:events';

import type { SCGTag } from '../types/universal-tag-system';

import type { KthuluArchitectureElement } from './go-ast-parser';
import type { OntologyUpdate } from './permagraph-controller';

export interface SemanticTriple {
  subject: string;
  predicate: string;
  object: string;
  context?: string;
}

export interface OWLClass {
  iri: string;
  label: string;
  comment?: string;
  superClasses?: string[];
  disjointWith?: string[];
}

export interface OWLProperty {
  iri: string;
  label: string;
  comment?: string;
  domain?: string;
  range?: string;
  type: 'ObjectProperty' | 'DataProperty';
}

export interface OWLIndividual {
  iri: string;
  type: string;
  label: string;
  properties: { [property: string]: any };
}

export class SemanticTripleGenerator extends EventEmitter {
  private readonly namespace = 'http://kthulu.io/ontology#';
  private readonly prefixes = {
    kth: this.namespace,
    owl: 'http://www.w3.org/2002/07/owl#',
    rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
  };

  /**
   * Generate semantic triples from Kthulu architectural elements
   */
  generateTriplesFromElements(
    elements: KthuluArchitectureElement[]
  ): SemanticTriple[] {
    const triples: SemanticTriple[] = [];

    // Generate ontology schema triples (TBox)
    const schemaTriples = this.generateSchemaTriples();
    triples.push(...schemaTriples);
    this.emitIncremental('schema', schemaTriples);

    // Generate instance triples (ABox)
    elements.forEach(element => {
      const elementTriples = this.generateElementTriples(element);
      triples.push(...elementTriples);
      this.emitIncremental(element.id, elementTriples);
    });

    // Generate relationship triples
    elements.forEach(element => {
      const relationshipTriples = this.generateRelationshipTriples(
        element,
        elements
      );
      triples.push(...relationshipTriples);
      this.emitIncremental(`${element.id}-relationships`, relationshipTriples);
    });

    return triples;
  }

  private emitIncremental(source: string, triples: SemanticTriple[]) {
    if (!triples.length) return;
    const update: OntologyUpdate = {
      type: 'add',
      triples,
      timestamp: new Date(),
      source,
    };
    this.emit('update', update);
  }

  /**
   * Generate semantic triples from universal SCG tags
   */
  generateTriplesFromTags(tags: SCGTag[]): SemanticTriple[] {
    const triples: SemanticTriple[] = [];

    triples.push(...this.generateSchemaTriples());

    const tagMap = new Map<string, SCGTag>();
    tags.forEach(t => tagMap.set(t.filePath, t));

    for (const tag of tags) {
      const subject = this.createIri(tag.filePath);
      const typeIri = `${this.namespace}${this.capitalizeFirst(tag.type)}`;
      triples.push({ subject, predicate: 'rdf:type', object: typeIri });
      triples.push({
        subject,
        predicate: `${this.namespace}framework`,
        object: tag.framework,
      });
      triples.push({
        subject,
        predicate: `${this.namespace}layer`,
        object: tag.layer,
      });

      // Dependencies
      for (const dep of tag.dependencies || []) {
        const object = this.createIri(dep);
        triples.push({
          subject,
          predicate: `${this.namespace}dependsOn`,
          object,
        });

        const depTag = tagMap.get(dep);
        if (depTag && depTag.framework !== tag.framework) {
          triples.push({
            subject,
            predicate: `${this.namespace}crossFramework`,
            object,
          });
        }
      }

      // Implements relationships
      for (const impl of tag.implements || []) {
        const object = this.createIri(impl);
        triples.push({
          subject,
          predicate: `${this.namespace}implements`,
          object,
        });
      }

      for (const use of tag.uses || []) {
        const object = this.createIri(use);
        triples.push({ subject, predicate: `${this.namespace}uses`, object });
      }
    }

    return triples;
  }

  private createIri(id: string): string {
    return `${this.namespace}${this.normalize(id)}`;
  }

  private normalize(value: string): string {
    return value
      .replace(/[^a-zA-Z0-9]/g, '_')
      .replace(/_+/g, '_')
      .toLowerCase();
  }

  /**
   * Generate OWL classes from the ontology schema
   */
  generateOWLClasses(): OWLClass[] {
    return [
      {
        iri: `${this.namespace}Module`,
        label: 'Module',
        comment: 'A Kthulu module containing use cases, adapters, and entities',
      },
      {
        iri: `${this.namespace}UseCase`,
        label: 'UseCase',
        comment: 'A domain use case implementing business logic',
        superClasses: [`${this.namespace}DomainComponent`],
      },
      {
        iri: `${this.namespace}Adapter`,
        label: 'Adapter',
        comment: 'An infrastructure adapter implementing ports',
        superClasses: [`${this.namespace}InfrastructureComponent`],
      },
      {
        iri: `${this.namespace}Port`,
        label: 'Port',
        comment:
          'An interface defining contract between domain and infrastructure',
        superClasses: [`${this.namespace}DomainComponent`],
      },
      {
        iri: `${this.namespace}DomainEntity`,
        label: 'DomainEntity',
        comment: 'A domain entity representing business concepts',
        superClasses: [`${this.namespace}DomainComponent`],
      },
      {
        iri: `${this.namespace}DomainEvent`,
        label: 'DomainEvent',
        comment: 'A domain event for decoupled communication',
        superClasses: [`${this.namespace}DomainComponent`],
      },
      {
        iri: `${this.namespace}DomainComponent`,
        label: 'DomainComponent',
        comment: 'Abstract class for domain layer components',
        disjointWith: [`${this.namespace}InfrastructureComponent`],
      },
      {
        iri: `${this.namespace}InfrastructureComponent`,
        label: 'InfrastructureComponent',
        comment: 'Abstract class for infrastructure layer components',
        disjointWith: [`${this.namespace}DomainComponent`],
      },
    ];
  }

  /**
   * Generate OWL properties from the ontology schema
   */
  generateOWLProperties(): OWLProperty[] {
    return [
      {
        iri: `${this.namespace}definesUseCase`,
        label: 'definesUseCase',
        comment: 'A module defines a use case',
        domain: `${this.namespace}Module`,
        range: `${this.namespace}UseCase`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}hasPort`,
        label: 'hasPort',
        comment: 'A module has a port',
        domain: `${this.namespace}Module`,
        range: `${this.namespace}Port`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}implementsPort`,
        label: 'implementsPort',
        comment: 'An adapter implements a port',
        domain: `${this.namespace}Adapter`,
        range: `${this.namespace}Port`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}usesPort`,
        label: 'usesPort',
        comment: 'A use case uses a port',
        domain: `${this.namespace}UseCase`,
        range: `${this.namespace}Port`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}dependsOnModule`,
        label: 'dependsOnModule',
        comment: 'A module depends on another module',
        domain: `${this.namespace}Module`,
        range: `${this.namespace}Module`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}emitsEvent`,
        label: 'emitsEvent',
        comment: 'A use case emits a domain event',
        domain: `${this.namespace}UseCase`,
        range: `${this.namespace}DomainEvent`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}handlesEvent`,
        label: 'handlesEvent',
        comment: 'An adapter handles a domain event',
        domain: `${this.namespace}Adapter`,
        range: `${this.namespace}DomainEvent`,
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}calls`,
        label: 'calls',
        comment: 'A component calls another component',
        type: 'ObjectProperty',
      },
      {
        iri: `${this.namespace}hasComplexity`,
        label: 'hasComplexity',
        comment: 'The complexity score of a component',
        type: 'DataProperty',
      },
      {
        iri: `${this.namespace}isExported`,
        label: 'isExported',
        comment: 'Whether a component is exported from its package',
        type: 'DataProperty',
      },
      {
        iri: `${this.namespace}hasTests`,
        label: 'hasTests',
        comment: 'Whether a component has associated tests',
        type: 'DataProperty',
      },
    ];
  }

  /**
   * Generate OWL individuals from architectural elements
   */
  generateOWLIndividuals(
    elements: KthuluArchitectureElement[]
  ): OWLIndividual[] {
    return elements.map(element => ({
      iri: `${this.namespace}${element.id}`,
      type: `${this.namespace}${this.capitalizeFirst(element.type)}`,
      label: element.name,
      properties: {
        [`${this.namespace}hasComplexity`]: element.metadata.complexity,
        [`${this.namespace}isExported`]: element.metadata.isExported,
        [`${this.namespace}hasTests`]: element.metadata.hasTests,
        [`${this.namespace}filePath`]: element.filePath,
        [`${this.namespace}packagePath`]: element.packagePath,
      },
    }));
  }

  /**
   * Export triples in Turtle format
   */
  exportToTurtle(triples: SemanticTriple[]): string {
    let turtle = '';

    // Add prefixes
    Object.entries(this.prefixes).forEach(([prefix, uri]) => {
      turtle += `@prefix ${prefix}: <${uri}> .\n`;
    });
    turtle += '\n';

    // Group triples by subject
    const groupedTriples = this.groupTriplesBySubject(triples);

    Object.entries(groupedTriples).forEach(([subject, predicateObjects]) => {
      turtle += `${this.formatIRI(subject)}\n`;

      const predicates = Object.entries(predicateObjects);
      predicates.forEach(([predicate, objects], index) => {
        const isLast = index === predicates.length - 1;
        turtle += `    ${this.formatIRI(predicate)} `;

        objects.forEach((object, objIndex) => {
          const isLastObject = objIndex === objects.length - 1;
          turtle += this.formatValue(object);
          if (!isLastObject) turtle += ', ';
        });

        turtle += isLast ? ' .\n\n' : ' ;\n';
      });
    });

    return turtle;
  }

  /**
   * Export triples in JSON-LD format
   */
  exportToJsonLD(triples: SemanticTriple[]): any {
    const context = {
      '@vocab': this.namespace,
      ...Object.fromEntries(
        Object.entries(this.prefixes).map(([prefix, uri]) => [prefix, uri])
      ),
    };

    const graph = this.groupTriplesBySubject(triples);
    const jsonLD = {
      '@context': context,
      '@graph': Object.entries(graph).map(([subject, predicateObjects]) => ({
        '@id': subject,
        ...Object.fromEntries(
          Object.entries(predicateObjects).map(([predicate, objects]) => [
            this.shortenIRI(predicate),
            objects.length === 1 ? objects[0] : objects,
          ])
        ),
      })),
    };

    return jsonLD;
  }

  private generateSchemaTriples(): SemanticTriple[] {
    const triples: SemanticTriple[] = [];

    // Generate class triples
    const classes = this.generateOWLClasses();
    classes.forEach(cls => {
      triples.push({
        subject: cls.iri,
        predicate: 'rdf:type',
        object: 'owl:Class',
      });

      triples.push({
        subject: cls.iri,
        predicate: 'rdfs:label',
        object: `"${cls.label}"`,
      });

      if (cls.comment) {
        triples.push({
          subject: cls.iri,
          predicate: 'rdfs:comment',
          object: `"${cls.comment}"`,
        });
      }

      cls.superClasses?.forEach(superClass => {
        triples.push({
          subject: cls.iri,
          predicate: 'rdfs:subClassOf',
          object: superClass,
        });
      });

      cls.disjointWith?.forEach(disjoint => {
        triples.push({
          subject: cls.iri,
          predicate: 'owl:disjointWith',
          object: disjoint,
        });
      });
    });

    // Generate property triples
    const properties = this.generateOWLProperties();
    properties.forEach(prop => {
      triples.push({
        subject: prop.iri,
        predicate: 'rdf:type',
        object: `owl:${prop.type}`,
      });

      triples.push({
        subject: prop.iri,
        predicate: 'rdfs:label',
        object: `"${prop.label}"`,
      });

      if (prop.comment) {
        triples.push({
          subject: prop.iri,
          predicate: 'rdfs:comment',
          object: `"${prop.comment}"`,
        });
      }

      if (prop.domain) {
        triples.push({
          subject: prop.iri,
          predicate: 'rdfs:domain',
          object: prop.domain,
        });
      }

      if (prop.range) {
        triples.push({
          subject: prop.iri,
          predicate: 'rdfs:range',
          object: prop.range,
        });
      }
    });

    return triples;
  }

  private generateElementTriples(
    element: KthuluArchitectureElement
  ): SemanticTriple[] {
    const triples: SemanticTriple[] = [];
    const elementIRI = `${this.namespace}${element.id}`;
    const typeIRI = `${this.namespace}${this.capitalizeFirst(element.type)}`;

    // Type assertion
    triples.push({
      subject: elementIRI,
      predicate: 'rdf:type',
      object: typeIRI,
    });

    // Label
    triples.push({
      subject: elementIRI,
      predicate: 'rdfs:label',
      object: `"${element.name}"`,
    });

    // Data properties
    triples.push({
      subject: elementIRI,
      predicate: `${this.namespace}hasComplexity`,
      object: `"${element.metadata.complexity}"^^xsd:integer`,
    });

    triples.push({
      subject: elementIRI,
      predicate: `${this.namespace}isExported`,
      object: `"${element.metadata.isExported}"^^xsd:boolean`,
    });

    triples.push({
      subject: elementIRI,
      predicate: `${this.namespace}hasTests`,
      object: `"${element.metadata.hasTests}"^^xsd:boolean`,
    });

    // File path
    triples.push({
      subject: elementIRI,
      predicate: `${this.namespace}filePath`,
      object: `"${element.filePath}"`,
    });

    return triples;
  }

  private generateRelationshipTriples(
    element: KthuluArchitectureElement,
    allElements: KthuluArchitectureElement[]
  ): SemanticTriple[] {
    const triples: SemanticTriple[] = [];
    const elementIRI = `${this.namespace}${element.id}`;

    // Dependencies
    element.dependencies.forEach(dep => {
      const targetElement = allElements.find(
        e => e.packagePath === dep || e.name === dep || dep.includes(e.name)
      );

      if (targetElement) {
        const targetIRI = `${this.namespace}${targetElement.id}`;
        triples.push({
          subject: elementIRI,
          predicate: `${this.namespace}calls`,
          object: targetIRI,
        });
      }
    });

    // Implementations
    element.implements.forEach(impl => {
      const interfaceElement = allElements.find(
        e => e.name === impl || impl.includes(e.name)
      );

      if (interfaceElement) {
        const interfaceIRI = `${this.namespace}${interfaceElement.id}`;
        triples.push({
          subject: elementIRI,
          predicate: `${this.namespace}implementsPort`,
          object: interfaceIRI,
        });
      }
    });

    return triples;
  }

  private groupTriplesBySubject(triples: SemanticTriple[]): {
    [subject: string]: { [predicate: string]: string[] };
  } {
    const grouped: { [subject: string]: { [predicate: string]: string[] } } =
      {};

    triples.forEach(triple => {
      if (!grouped[triple.subject]) {
        grouped[triple.subject] = {};
      }

      if (!grouped[triple.subject][triple.predicate]) {
        grouped[triple.subject][triple.predicate] = [];
      }

      grouped[triple.subject][triple.predicate].push(triple.object);
    });

    return grouped;
  }

  private formatIRI(iri: string): string {
    // Convert full IRIs to prefixed form
    for (const [prefix, uri] of Object.entries(this.prefixes)) {
      if (iri.startsWith(uri)) {
        return iri.replace(uri, `${prefix}:`);
      }
    }
    return `<${iri}>`;
  }

  private shortenIRI(iri: string): string {
    for (const [prefix, uri] of Object.entries(this.prefixes)) {
      if (iri.startsWith(uri)) {
        return iri.replace(uri, `${prefix}:`);
      }
    }
    return iri;
  }

  private formatValue(value: string): string {
    if (value.startsWith('"') || value.startsWith('<') || value.includes(':')) {
      return value;
    }
    return `<${value}>`;
  }

  private capitalizeFirst(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
