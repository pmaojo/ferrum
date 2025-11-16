import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import {
  Plus,
  Minus,
  Eye,
  Code,
  Filter,
  Database,
  GitBranch,
  Zap,
  Target,
  Package,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Triple {
  id: string;
  subject: TripleElement;
  predicate: TripleElement;
  object: TripleElement;
  optional: boolean;
}

interface TripleElement {
  type: 'variable' | 'uri' | 'literal' | 'class' | 'property';
  value: string;
  prefix?: string;
}

interface Filter {
  id: string;
  variable: string;
  operator: '=' | '!=' | '>' | '<' | '>=' | '<=' | 'CONTAINS' | 'REGEX';
  value: string;
  type: 'string' | 'number' | 'boolean';
}

interface GraphicalSPARQLBuilderProps {
  onQueryChange: (query: string) => void;
  initialQuery?: string;
}

const kthuluClasses = [
  {
    value: 'kth:Module',
    label: 'Module',
    icon: Package,
    description: 'Bounded context module',
  },
  {
    value: 'kth:UseCase',
    label: 'UseCase',
    icon: Target,
    description: 'Domain use case',
  },
  {
    value: 'kth:Port',
    label: 'Port',
    icon: GitBranch,
    description: 'Interface port',
  },
  {
    value: 'kth:Adapter',
    label: 'Adapter',
    icon: Database,
    description: 'Infrastructure adapter',
  },
  {
    value: 'kth:DomainEntity',
    label: 'DomainEntity',
    icon: Package,
    description: 'Domain entity',
  },
  {
    value: 'kth:DomainEvent',
    label: 'DomainEvent',
    icon: Zap,
    description: 'Domain event',
  },
  {
    value: 'kth:DomainComponent',
    label: 'DomainComponent',
    icon: Package,
    description: 'Domain component',
  },
  {
    value: 'kth:InfrastructureComponent',
    label: 'InfrastructureComponent',
    icon: Database,
    description: 'Infrastructure component',
  },
];

const kthuluProperties = [
  {
    value: 'kth:definesUseCase',
    label: 'definesUseCase',
    description: 'Module defines use case',
  },
  { value: 'kth:hasPort', label: 'hasPort', description: 'Module has port' },
  {
    value: 'kth:implementsPort',
    label: 'implementsPort',
    description: 'Adapter implements port',
  },
  {
    value: 'kth:usesPort',
    label: 'usesPort',
    description: 'Use case uses port',
  },
  {
    value: 'kth:dependsOnModule',
    label: 'dependsOnModule',
    description: 'Module depends on module',
  },
  {
    value: 'kth:emitsEvent',
    label: 'emitsEvent',
    description: 'Use case emits event',
  },
  {
    value: 'kth:handlesEvent',
    label: 'handlesEvent',
    description: 'Adapter handles event',
  },
  {
    value: 'kth:calls',
    label: 'calls',
    description: 'Component calls component',
  },
  { value: 'rdfs:label', label: 'label', description: 'Human readable label' },
  { value: 'rdf:type', label: 'type', description: 'RDF type' },
];

const commonPrefixes = {
  kth: 'http://kthulu.io/ontology#',
  owl: 'http://www.w3.org/2002/07/owl#',
  rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
};

/**
 * @kthulu:extend - Graphical SPARQL query builder for Kthulu ontology
 * Provides drag-and-drop interface for building semantic queries
 */
export function GraphicalSPARQLBuilder({
  onQueryChange,
  initialQuery,
}: GraphicalSPARQLBuilderProps) {
  const [triples, setTriples] = useState<Triple[]>([]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [selectVariables, setSelectVariables] = useState<string[]>(['?module']);
  const [distinct, setDistinct] = useState(false);
  const [limit, setLimit] = useState<number | null>(null);
  const [orderBy, setOrderBy] = useState<string>('');
  const [queryType, setQueryType] = useState<'SELECT' | 'ASK' | 'CONSTRUCT'>(
    'SELECT'
  );
  const [ontology, setOntology] = useState('kth');
  const [savedQueries, setSavedQueries] = useState<
    { id: string; name: string; query: string }[]
  >([]);
  const [queryName, setQueryName] = useState('');

  const classes = ontology === 'kth' ? kthuluClasses : [];
  const properties = ontology === 'kth' ? kthuluProperties : [];
  const prefixes = ontology === 'kth' ? commonPrefixes : {};

  useEffect(() => {
    const stored = localStorage.getItem('sparqlBuilderSaved');
    if (stored) {
      try {
        setSavedQueries(JSON.parse(stored));
      } catch {
        // ignore
      }
    }
  }, []);

  const generateQuery = useCallback(() => {
    let query = '';

    // Add prefixes
    Object.entries(prefixes).forEach(([prefix, uri]) => {
      query += `PREFIX ${prefix}: <${uri}>\n`;
    });
    query += '\n';

    // Add query type
    if (queryType === 'SELECT') {
      query += `SELECT ${distinct ? 'DISTINCT ' : ''}`;
      if (selectVariables.length > 0) {
        query += selectVariables.join(' ');
      } else {
        query += '*';
      }
    } else if (queryType === 'ASK') {
      query += 'ASK';
    } else if (queryType === 'CONSTRUCT') {
      query += 'CONSTRUCT {\n';
      triples.forEach((triple) => {
        if (!triple.optional) {
          query += `  ${triple.subject.value} ${triple.predicate.value} ${triple.object.value} .\n`;
        }
      });
      query += '}';
    }

    query += ' WHERE {\n';

    // Add triples
    triples.forEach((triple) => {
      const tripleStr = `  ${triple.subject.value} ${triple.predicate.value} ${triple.object.value} .`;
      if (triple.optional) {
        query += `  OPTIONAL { ${tripleStr.trim()} }\n`;
      } else {
        query += `${tripleStr}\n`;
      }
    });

    // Add filters
    filters.forEach((filter) => {
      let filterStr = '';
      if (filter.operator === 'CONTAINS') {
        filterStr = `CONTAINS(${filter.variable}, "${filter.value}")`;
      } else if (filter.operator === 'REGEX') {
        filterStr = `REGEX(${filter.variable}, "${filter.value}")`;
      } else {
        const value =
          filter.type === 'string' ? `"${filter.value}"` : filter.value;
        filterStr = `${filter.variable} ${filter.operator} ${value}`;
      }
      query += `  FILTER(${filterStr})\n`;
    });

    query += '}';

    // Add ORDER BY
    if (orderBy) {
      query += `\nORDER BY ${orderBy}`;
    }

    // Add LIMIT
    if (limit && limit > 0) {
      query += `\nLIMIT ${limit}`;
    }

    return query;
  }, [triples, filters, selectVariables, distinct, limit, orderBy, queryType]);

  useEffect(() => {
    const query = generateQuery();
    onQueryChange(query);
  }, [generateQuery, onQueryChange]);

  const addTriple = () => {
    const newTriple: Triple = {
      id: `triple-${Date.now()}`,
      subject: { type: 'variable', value: '?subject' },
      predicate: { type: 'property', value: 'rdf:type' },
      object: { type: 'class', value: 'kth:Module' },
      optional: false,
    };
    setTriples([...triples, newTriple]);
  };

  const removeTriple = (id: string) => {
    setTriples(triples.filter((t) => t.id !== id));
  };

  const updateTriple = (id: string, field: keyof Triple, value: any) => {
    setTriples(
      triples.map((t) => (t.id === id ? { ...t, [field]: value } : t))
    );
  };

  const updateTripleElement = (
    tripleId: string,
    element: 'subject' | 'predicate' | 'object',
    updates: Partial<TripleElement>
  ) => {
    setTriples(
      triples.map((t) =>
        t.id === tripleId
          ? { ...t, [element]: { ...t[element], ...updates } }
          : t
      )
    );
  };

  const addFilter = () => {
    const newFilter: Filter = {
      id: `filter-${Date.now()}`,
      variable: '?variable',
      operator: '=',
      value: '',
      type: 'string',
    };
    setFilters([...filters, newFilter]);
  };

  const removeFilter = (id: string) => {
    setFilters(filters.filter((f) => f.id !== id));
  };

  const updateFilter = (id: string, field: keyof Filter, value: any) => {
    setFilters(
      filters.map((f) => (f.id === id ? { ...f, [field]: value } : f))
    );
  };

  const addSelectVariable = () => {
    const newVar = `?var${selectVariables.length + 1}`;
    setSelectVariables([...selectVariables, newVar]);
  };

  const removeSelectVariable = (index: number) => {
    setSelectVariables(selectVariables.filter((_, i) => i !== index));
  };

  const updateSelectVariable = (index: number, value: string) => {
    setSelectVariables(
      selectVariables.map((v, i) => (i === index ? value : v))
    );
  };

  const loadTemplate = (template: string) => {
    switch (template) {
      case 'modules':
        setTriples([
          {
            id: 'triple-1',
            subject: { type: 'variable', value: '?module' },
            predicate: { type: 'property', value: 'rdf:type' },
            object: { type: 'class', value: 'kth:Module' },
            optional: false,
          },
        ]);
        setSelectVariables(['?module']);
        break;
      case 'dependencies':
        setTriples([
          {
            id: 'triple-1',
            subject: { type: 'variable', value: '?module' },
            predicate: { type: 'property', value: 'rdf:type' },
            object: { type: 'class', value: 'kth:Module' },
            optional: false,
          },
          {
            id: 'triple-2',
            subject: { type: 'variable', value: '?module' },
            predicate: { type: 'property', value: 'kth:dependsOnModule' },
            object: { type: 'variable', value: '?dependency' },
            optional: false,
          },
        ]);
        setSelectVariables(['?module', '?dependency']);
        break;
      case 'violations':
        setTriples([
          {
            id: 'triple-1',
            subject: { type: 'variable', value: '?domain' },
            predicate: { type: 'property', value: 'rdf:type' },
            object: { type: 'class', value: 'kth:DomainComponent' },
            optional: false,
          },
          {
            id: 'triple-2',
            subject: { type: 'variable', value: '?infra' },
            predicate: { type: 'property', value: 'rdf:type' },
            object: { type: 'class', value: 'kth:InfrastructureComponent' },
            optional: false,
          },
          {
            id: 'triple-3',
            subject: { type: 'variable', value: '?domain' },
            predicate: { type: 'property', value: 'kth:calls' },
            object: { type: 'variable', value: '?infra' },
            optional: false,
          },
        ]);
        setSelectVariables(['?domain', '?infra']);
        break;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Code className="w-5 h-5" />
          Graphical SPARQL Builder
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between mb-4">
          <div className="space-y-1">
            <Label>Ontology</Label>
            <Select value={ontology} onValueChange={setOntology}>
              <SelectTrigger className="w-40 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="kth">Kthulu</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end gap-2">
            <Input
              value={queryName}
              onChange={(e) => setQueryName(e.target.value)}
              placeholder="Query name"
              className="h-8"
            />
            <Button
              onClick={() => {
                const q = generateQuery();
                const newSaved = [
                  ...savedQueries,
                  {
                    id: Date.now().toString(),
                    name: queryName || `Query ${savedQueries.length + 1}`,
                    query: q,
                  },
                ];
                setSavedQueries(newSaved);
                localStorage.setItem(
                  'sparqlBuilderSaved',
                  JSON.stringify(newSaved)
                );
                setQueryName('');
              }}
              size="sm"
            >
              Save
            </Button>
          </div>
        </div>
        <Tabs defaultValue="builder" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="builder">Query Builder</TabsTrigger>
            <TabsTrigger value="templates">Templates</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="builder" className="space-y-6 mt-4">
            {/* Query Type and Options */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Query Type</Label>
                <Select
                  value={queryType}
                  onValueChange={(value) => setQueryType(value as any)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SELECT">SELECT</SelectItem>
                    <SelectItem value="ASK">ASK</SelectItem>
                    <SelectItem value="CONSTRUCT">CONSTRUCT</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2 pt-6">
                <Switch
                  id="distinct"
                  checked={distinct}
                  onCheckedChange={setDistinct}
                />
                <Label htmlFor="distinct">DISTINCT</Label>
              </div>

              <div className="space-y-2">
                <Label>Limit</Label>
                <Input
                  type="number"
                  value={limit || ''}
                  onChange={(e) =>
                    setLimit(e.target.value ? parseInt(e.target.value) : null)
                  }
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2">
                <Label>Order By</Label>
                <Input
                  value={orderBy}
                  onChange={(e) => setOrderBy(e.target.value)}
                  placeholder="?variable"
                />
              </div>
            </div>

            {/* Select Variables */}
            {queryType === 'SELECT' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Select Variables</Label>
                  <Button
                    onClick={addSelectVariable}
                    size="sm"
                    variant="outline"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add Variable
                  </Button>
                </div>
                <div className="space-y-2">
                  {selectVariables.map((variable, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Input
                        value={variable}
                        onChange={(e) =>
                          updateSelectVariable(index, e.target.value)
                        }
                        placeholder="?variable"
                        className="flex-1"
                      />
                      <Button
                        onClick={() => removeSelectVariable(index)}
                        size="sm"
                        variant="ghost"
                      >
                        <Minus className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Separator />

            {/* Triple Patterns */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Triple Patterns</Label>
                <Button onClick={addTriple} size="sm" variant="outline">
                  <Plus className="w-4 h-4 mr-1" />
                  Add Triple
                </Button>
              </div>

              <ScrollArea className="h-64">
                <div className="space-y-3">
                  {triples.map((triple) => (
                    <Card key={triple.id} className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={triple.optional ? 'secondary' : 'default'}
                          >
                            {triple.optional ? 'OPTIONAL' : 'REQUIRED'}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={triple.optional}
                            onCheckedChange={(checked) =>
                              updateTriple(triple.id, 'optional', checked)
                            }
                          />
                          <Label className="text-sm">Optional</Label>
                          <Button
                            onClick={() => removeTriple(triple.id)}
                            size="sm"
                            variant="ghost"
                          >
                            <Minus className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2">
                        {/* Subject */}
                        <div className="space-y-2">
                          <Label className="text-xs">Subject</Label>
                          <Select
                            value={triple.subject.type}
                            onValueChange={(value) =>
                              updateTripleElement(triple.id, 'subject', {
                                type: value as any,
                              })
                            }
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="variable">Variable</SelectItem>
                              <SelectItem value="uri">URI</SelectItem>
                              <SelectItem value="class">Class</SelectItem>
                            </SelectContent>
                          </Select>
                          {triple.subject.type === 'class' ? (
                            <Select
                              value={triple.subject.value}
                              onValueChange={(value) =>
                                updateTripleElement(triple.id, 'subject', {
                                  value,
                                })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {classes.map((cls) => (
                                  <SelectItem key={cls.value} value={cls.value}>
                                    {cls.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input
                              value={triple.subject.value}
                              onChange={(e) =>
                                updateTripleElement(triple.id, 'subject', {
                                  value: e.target.value,
                                })
                              }
                              placeholder={
                                triple.subject.type === 'variable'
                                  ? '?variable'
                                  : 'URI'
                              }
                              className="h-8"
                            />
                          )}
                        </div>

                        {/* Predicate */}
                        <div className="space-y-2">
                          <Label className="text-xs">Predicate</Label>
                          <Select
                            value={triple.predicate.type}
                            onValueChange={(value) =>
                              updateTripleElement(triple.id, 'predicate', {
                                type: value as any,
                              })
                            }
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="property">Property</SelectItem>
                              <SelectItem value="variable">Variable</SelectItem>
                              <SelectItem value="uri">URI</SelectItem>
                            </SelectContent>
                          </Select>
                          {triple.predicate.type === 'property' ? (
                            <Select
                              value={triple.predicate.value}
                              onValueChange={(value) =>
                                updateTripleElement(triple.id, 'predicate', {
                                  value,
                                })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {properties.map((prop) => (
                                  <SelectItem
                                    key={prop.value}
                                    value={prop.value}
                                  >
                                    {prop.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input
                              value={triple.predicate.value}
                              onChange={(e) =>
                                updateTripleElement(triple.id, 'predicate', {
                                  value: e.target.value,
                                })
                              }
                              placeholder={
                                triple.predicate.type === 'variable'
                                  ? '?variable'
                                  : 'URI'
                              }
                              className="h-8"
                            />
                          )}
                        </div>

                        {/* Object */}
                        <div className="space-y-2">
                          <Label className="text-xs">Object</Label>
                          <Select
                            value={triple.object.type}
                            onValueChange={(value) =>
                              updateTripleElement(triple.id, 'object', {
                                type: value as any,
                              })
                            }
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="variable">Variable</SelectItem>
                              <SelectItem value="class">Class</SelectItem>
                              <SelectItem value="literal">Literal</SelectItem>
                              <SelectItem value="uri">URI</SelectItem>
                            </SelectContent>
                          </Select>
                          {triple.object.type === 'class' ? (
                            <Select
                              value={triple.object.value}
                              onValueChange={(value) =>
                                updateTripleElement(triple.id, 'object', {
                                  value,
                                })
                              }
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {classes.map((cls) => (
                                  <SelectItem key={cls.value} value={cls.value}>
                                    {cls.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <Input
                              value={triple.object.value}
                              onChange={(e) =>
                                updateTripleElement(triple.id, 'object', {
                                  value: e.target.value,
                                })
                              }
                              placeholder={
                                triple.object.type === 'variable'
                                  ? '?variable'
                                  : triple.object.type === 'literal'
                                    ? '"literal"'
                                    : 'URI'
                              }
                              className="h-8"
                            />
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}

                  {triples.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      <Database className="w-8 h-8 mx-auto mb-2" />
                      <p>No triple patterns defined</p>
                      <p className="text-sm">
                        Click "Add Triple" to start building your query
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>

            <Separator />

            {/* Saved Queries */}
            <div className="space-y-2">
              <Label>Saved Queries</Label>
              {savedQueries.length === 0 && (
                <div className="text-sm text-muted-foreground">
                  No saved queries
                </div>
              )}
              {savedQueries.map((q) => (
                <div key={q.id} className="flex items-center justify-between">
                  <Button
                    variant="link"
                    className="p-0 h-auto"
                    onClick={() => onQueryChange(q.query)}
                  >
                    {q.name}
                  </Button>
                </div>
              ))}
            </div>

            <Separator />

            {/* Filters */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Filters</Label>
                <Button onClick={addFilter} size="sm" variant="outline">
                  <Filter className="w-4 h-4 mr-1" />
                  Add Filter
                </Button>
              </div>

              <div className="space-y-2">
                {filters.map((filter) => (
                  <Card key={filter.id} className="p-3">
                    <div className="grid grid-cols-4 gap-2 items-end">
                      <div className="space-y-1">
                        <Label className="text-xs">Variable</Label>
                        <Input
                          value={filter.variable}
                          onChange={(e) =>
                            updateFilter(filter.id, 'variable', e.target.value)
                          }
                          placeholder="?variable"
                          className="h-8"
                        />
                      </div>

                      <div className="space-y-1">
                        <Label className="text-xs">Operator</Label>
                        <Select
                          value={filter.operator}
                          onValueChange={(value) =>
                            updateFilter(filter.id, 'operator', value)
                          }
                        >
                          <SelectTrigger className="h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="=">=</SelectItem>
                            <SelectItem value="!=">!=</SelectItem>
                            <SelectItem value=">">&gt;</SelectItem>
                            <SelectItem value="<">&lt;</SelectItem>
                            <SelectItem value=">=">&gt;=</SelectItem>
                            <SelectItem value="<=">&lt;=</SelectItem>
                            <SelectItem value="CONTAINS">CONTAINS</SelectItem>
                            <SelectItem value="REGEX">REGEX</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1">
                        <Label className="text-xs">Value</Label>
                        <Input
                          value={filter.value}
                          onChange={(e) =>
                            updateFilter(filter.id, 'value', e.target.value)
                          }
                          placeholder="value"
                          className="h-8"
                        />
                      </div>

                      <Button
                        onClick={() => removeFilter(filter.id)}
                        size="sm"
                        variant="ghost"
                        className="h-8"
                      >
                        <Minus className="w-4 h-4" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="templates" className="space-y-4 mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => loadTemplate('modules')}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <Package className="w-8 h-8 text-blue-600" />
                    <div>
                      <h3 className="font-semibold">List All Modules</h3>
                      <p className="text-sm text-muted-foreground">
                        Find all modules in the system
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => loadTemplate('dependencies')}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <GitBranch className="w-8 h-8 text-green-600" />
                    <div>
                      <h3 className="font-semibold">Module Dependencies</h3>
                      <p className="text-sm text-muted-foreground">
                        Show dependencies between modules
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => loadTemplate('violations')}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <Zap className="w-8 h-8 text-red-600" />
                    <div>
                      <h3 className="font-semibold">DIP Violations</h3>
                      <p className="text-sm text-muted-foreground">
                        Find dependency inversion violations
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="preview" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-4 h-4" />
                  Generated SPARQL Query
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <pre className="text-sm font-mono bg-muted p-4 rounded whitespace-pre-wrap">
                    {generateQuery()}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
