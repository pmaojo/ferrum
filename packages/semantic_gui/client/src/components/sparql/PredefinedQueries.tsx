import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search,
  Play,
  Star,
  Package,
  Target,
  GitBranch,
  Database,
  Zap,
  AlertTriangle,
  BarChart3,
  Network,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface PredefinedQuery {
  id: string;
  name: string;
  description: string;
  category:
    | 'architecture'
    | 'validation'
    | 'analysis'
    | 'dependencies'
    | 'metrics';
  query: string;
  parameters?: QueryParameter[];
  complexity: 'simple' | 'intermediate' | 'advanced';
  tags: string[];
  icon: any;
  color: string;
}

interface QueryParameter {
  name: string;
  type: 'string' | 'number' | 'boolean';
  description: string;
  defaultValue?: any;
  required: boolean;
}

interface PredefinedQueriesProps {
  onQuerySelect: (query: string) => void;
  onExecuteQuery: (query: string) => void;
  favorites: string[];
  onToggleFavorite: (queryId: string) => void;
  presets?: { id: string; query: string }[];
}

const predefinedQueries: PredefinedQuery[] = [
  // Architecture Queries
  {
    id: 'list-modules',
    name: 'List All Modules',
    description: 'Get all modules with their names and descriptions',
    category: 'architecture',
    complexity: 'simple',
    tags: ['modules', 'basic', 'overview'],
    icon: Package,
    color: 'text-blue-600 bg-blue-50 border-blue-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?module ?name ?description WHERE {
  ?module a kth:Module .
  OPTIONAL { ?module rdfs:label ?name }
  OPTIONAL { ?module rdfs:comment ?description }
}
ORDER BY ?name`,
  },
  {
    id: 'module-usecases',
    name: 'Module Use Cases',
    description: 'Find all use cases defined by each module',
    category: 'architecture',
    complexity: 'simple',
    tags: ['modules', 'usecases', 'structure'],
    icon: Target,
    color: 'text-green-600 bg-green-50 border-green-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?module ?moduleLabel ?usecase ?usecaseLabel WHERE {
  ?module a kth:Module .
  ?module kth:definesUseCase ?usecase .
  ?usecase a kth:UseCase .
  OPTIONAL { ?module rdfs:label ?moduleLabel }
  OPTIONAL { ?usecase rdfs:label ?usecaseLabel }
}
ORDER BY ?moduleLabel ?usecaseLabel`,
  },
  {
    id: 'port-implementations',
    name: 'Port Implementation Status',
    description: 'Show which ports are implemented by adapters',
    category: 'architecture',
    complexity: 'intermediate',
    tags: ['ports', 'adapters', 'implementation'],
    icon: GitBranch,
    color: 'text-purple-600 bg-purple-50 border-purple-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?port ?portLabel ?adapter ?adapterLabel ?implemented WHERE {
  ?port a kth:Port .
  OPTIONAL { ?port rdfs:label ?portLabel }
  OPTIONAL {
    ?adapter kth:implementsPort ?port .
    ?adapter rdfs:label ?adapterLabel .
    BIND("Yes" AS ?implemented)
  }
  FILTER(!BOUND(?implemented) || ?implemented = "Yes")
}
ORDER BY ?portLabel`,
  },

  // Validation Queries
  {
    id: 'dip-violations',
    name: 'DIP Violations',
    description: 'Find components violating Dependency Inversion Principle',
    category: 'validation',
    complexity: 'intermediate',
    tags: ['dip', 'violations', 'architecture'],
    icon: AlertTriangle,
    color: 'text-red-600 bg-red-50 border-red-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?domainComponent ?infrastructureComponent ?domainLabel ?infraLabel WHERE {
  ?domainComponent a kth:DomainComponent .
  ?infrastructureComponent a kth:InfrastructureComponent .
  ?domainComponent kth:calls ?infrastructureComponent .
  OPTIONAL { ?domainComponent rdfs:label ?domainLabel }
  OPTIONAL { ?infrastructureComponent rdfs:label ?infraLabel }
}
ORDER BY ?domainLabel`,
  },
  {
    id: 'bounded-context-violations',
    name: 'Bounded Context Violations',
    description: 'Find entities used across module boundaries',
    category: 'validation',
    complexity: 'advanced',
    tags: ['ddd', 'bounded-context', 'violations'],
    icon: AlertTriangle,
    color: 'text-orange-600 bg-orange-50 border-orange-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?sourceModule ?targetModule ?entityLabel WHERE {
  ?entity a kth:DomainEntity .
  ?sourceModule kth:definesEntity ?entity .
  ?targetModule kth:usesEntity ?entity .
  FILTER(?sourceModule != ?targetModule)
  OPTIONAL { ?entity rdfs:label ?entityLabel }
}
ORDER BY ?entityLabel`,
  },
  {
    id: 'aggregate-integrity',
    name: 'Aggregate Integrity Check',
    description: 'Verify that entities belong to only one aggregate',
    category: 'validation',
    complexity: 'advanced',
    tags: ['ddd', 'aggregates', 'integrity'],
    icon: Database,
    color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?aggregate1 ?aggregate2 ?entityLabel WHERE {
  ?entity a kth:DomainEntity .
  ?entity kth:partOfAggregate ?aggregate1 .
  ?entity kth:partOfAggregate ?aggregate2 .
  FILTER(?aggregate1 != ?aggregate2)
  OPTIONAL { ?entity rdfs:label ?entityLabel }
}
ORDER BY ?entityLabel`,
  },

  // Dependency Analysis
  {
    id: 'module-dependencies',
    name: 'Module Dependencies',
    description: 'Show direct dependencies between modules',
    category: 'dependencies',
    complexity: 'simple',
    tags: ['modules', 'dependencies', 'structure'],
    icon: Network,
    color: 'text-cyan-600 bg-cyan-50 border-cyan-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?module ?dependency ?moduleLabel ?depLabel WHERE {
  ?module a kth:Module .
  ?module kth:dependsOnModule ?dependency .
  ?dependency a kth:Module .
  OPTIONAL { ?module rdfs:label ?moduleLabel }
  OPTIONAL { ?dependency rdfs:label ?depLabel }
}
ORDER BY ?moduleLabel ?depLabel`,
  },
  {
    id: 'dependency-cycles',
    name: 'Dependency Cycles',
    description: 'Detect circular dependencies between modules',
    category: 'dependencies',
    complexity: 'advanced',
    tags: ['cycles', 'dependencies', 'violations'],
    icon: AlertTriangle,
    color: 'text-red-600 bg-red-50 border-red-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?module1 ?module2 ?label1 ?label2 WHERE {
  ?module1 a kth:Module .
  ?module2 a kth:Module .
  ?module1 kth:dependsOnModule+ ?module2 .
  ?module2 kth:dependsOnModule+ ?module1 .
  FILTER(?module1 != ?module2)
  OPTIONAL { ?module1 rdfs:label ?label1 }
  OPTIONAL { ?module2 rdfs:label ?label2 }
}
ORDER BY ?label1 ?label2`,
  },
  {
    id: 'impact-analysis',
    name: 'Impact Analysis',
    description: 'Find all modules that depend on a specific module',
    category: 'analysis',
    complexity: 'intermediate',
    tags: ['impact', 'dependencies', 'analysis'],
    icon: BarChart3,
    color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
    parameters: [
      {
        name: 'targetModule',
        type: 'string',
        description: 'The module to analyze impact for',
        required: true,
      },
    ],
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dependentModule ?dependentLabel ?distance WHERE {
  ?dependentModule kth:dependsOnModule+ ?targetModule .
  ?targetModule rdfs:label "{{targetModule}}" .
  OPTIONAL { ?dependentModule rdfs:label ?dependentLabel }
  # Calculate dependency distance (simplified)
  BIND(1 AS ?distance)
}
ORDER BY ?distance ?dependentLabel`,
  },

  // Metrics Queries
  {
    id: 'module-complexity',
    name: 'Module Complexity Metrics',
    description: 'Calculate complexity metrics for each module',
    category: 'metrics',
    complexity: 'advanced',
    tags: ['metrics', 'complexity', 'analysis'],
    icon: BarChart3,
    color: 'text-purple-600 bg-purple-50 border-purple-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?module ?moduleLabel ?usecaseCount ?portCount ?adapterCount ?dependencyCount WHERE {
  ?module a kth:Module .
  OPTIONAL { ?module rdfs:label ?moduleLabel }
  
  # Count use cases
  {
    SELECT ?module (COUNT(?usecase) AS ?usecaseCount) WHERE {
      ?module kth:definesUseCase ?usecase .
    } GROUP BY ?module
  }
  
  # Count ports
  {
    SELECT ?module (COUNT(?port) AS ?portCount) WHERE {
      ?module kth:hasPort ?port .
    } GROUP BY ?module
  }
  
  # Count adapters
  {
    SELECT ?module (COUNT(?adapter) AS ?adapterCount) WHERE {
      ?adapter kth:belongsToModule ?module .
      ?adapter a kth:Adapter .
    } GROUP BY ?module
  }
  
  # Count dependencies
  {
    SELECT ?module (COUNT(?dependency) AS ?dependencyCount) WHERE {
      ?module kth:dependsOnModule ?dependency .
    } GROUP BY ?module
  }
}
ORDER BY DESC(?usecaseCount)`,
  },
  {
    id: 'event-flow-analysis',
    name: 'Event Flow Analysis',
    description: 'Analyze domain event flows between components',
    category: 'analysis',
    complexity: 'intermediate',
    tags: ['events', 'flow', 'domain'],
    icon: Zap,
    color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?event ?emitter ?handler ?eventLabel ?emitterLabel ?handlerLabel WHERE {
  ?event a kth:DomainEvent .
  ?emitter kth:emitsEvent ?event .
  ?handler kth:handlesEvent ?event .
  OPTIONAL { ?event rdfs:label ?eventLabel }
  OPTIONAL { ?emitter rdfs:label ?emitterLabel }
  OPTIONAL { ?handler rdfs:label ?handlerLabel }
}
ORDER BY ?eventLabel`,
  },
];

const categoryConfig = {
  architecture: {
    label: 'Architecture',
    icon: Package,
    color: 'text-blue-600',
  },
  validation: {
    label: 'Validation',
    icon: AlertTriangle,
    color: 'text-red-600',
  },
  analysis: { label: 'Analysis', icon: BarChart3, color: 'text-purple-600' },
  dependencies: {
    label: 'Dependencies',
    icon: Network,
    color: 'text-cyan-600',
  },
  metrics: { label: 'Metrics', icon: BarChart3, color: 'text-indigo-600' },
};

const complexityConfig = {
  simple: { label: 'Simple', color: 'text-green-600 bg-green-50' },
  intermediate: {
    label: 'Intermediate',
    color: 'text-yellow-600 bg-yellow-50',
  },
  advanced: { label: 'Advanced', color: 'text-red-600 bg-red-50' },
};

/**
 * @kthulu:extend - Predefined SPARQL queries for common architectural analysis
 * Provides categorized queries with parameters and complexity indicators
 */
export function PredefinedQueries({
  onQuerySelect,
  onExecuteQuery,
  favorites,
  onToggleFavorite,
  presets = [],
}: PredefinedQueriesProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedComplexity, setSelectedComplexity] = useState<string>('all');
  const [parameterValues, setParameterValues] = useState<
    Record<string, Record<string, any>>
  >({});

  const allQueries = useMemo<PredefinedQuery[]>(() => {
    const dynamic = presets.map((p) => ({
      id: p.id,
      name: p.id,
      description: '',
      category: 'analysis' as const,
      complexity: 'simple' as const,
      tags: [],
      icon: Network,
      color: 'text-gray-600 bg-gray-50 border-gray-200',
      query: p.query,
    }));
    return [...predefinedQueries, ...dynamic];
  }, [presets]);

  const filteredQueries = allQueries.filter((query) => {
    const matchesSearch =
      query.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      query.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      query.tags.some((tag) =>
        tag.toLowerCase().includes(searchTerm.toLowerCase())
      );

    const matchesCategory =
      selectedCategory === 'all' || query.category === selectedCategory;
    const matchesComplexity =
      selectedComplexity === 'all' || query.complexity === selectedComplexity;

    return matchesSearch && matchesCategory && matchesComplexity;
  });

  const favoriteQueries = filteredQueries.filter((q) =>
    favorites.includes(q.id)
  );
  const otherQueries = filteredQueries.filter((q) => !favorites.includes(q.id));

  const handleExecuteQuery = (query: PredefinedQuery) => {
    let finalQuery = query.query;

    // Replace parameters if any
    if (query.parameters) {
      const params = parameterValues[query.id] || {};
      query.parameters.forEach((param) => {
        const value = params[param.name] || param.defaultValue || '';
        finalQuery = finalQuery.replace(
          new RegExp(`{{${param.name}}}`, 'g'),
          value
        );
      });
    }

    onExecuteQuery(finalQuery);
  };

  const handleSelectQuery = (query: PredefinedQuery) => {
    let finalQuery = query.query;

    // Replace parameters if any
    if (query.parameters) {
      const params = parameterValues[query.id] || {};
      query.parameters.forEach((param) => {
        const value = params[param.name] || param.defaultValue || '';
        finalQuery = finalQuery.replace(
          new RegExp(`{{${param.name}}}`, 'g'),
          value
        );
      });
    }

    onQuerySelect(finalQuery);
  };

  const updateParameterValue = (
    queryId: string,
    paramName: string,
    value: any
  ) => {
    setParameterValues((prev) => ({
      ...prev,
      [queryId]: {
        ...prev[queryId],
        [paramName]: value,
      },
    }));
  };

  const renderQueryCard = (query: PredefinedQuery) => {
    const IconComponent = query.icon;
    const isFavorite = favorites.includes(query.id);
    const categoryInfo = categoryConfig[query.category];
    const complexityInfo = complexityConfig[query.complexity];

    return (
      <Card
        key={query.id}
        className={cn('transition-all hover:shadow-md', query.color)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={cn('p-2 rounded-lg', query.color)}>
                <IconComponent className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-base">{query.name}</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {query.description}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggleFavorite(query.id)}
              className="shrink-0"
            >
              <Star
                className={cn(
                  'w-4 h-4',
                  isFavorite && 'fill-current text-yellow-500'
                )}
              />
            </Button>
          </div>

          <div className="flex items-center gap-2 mt-2">
            <Badge variant="outline" className={categoryInfo.color}>
              {categoryInfo.label}
            </Badge>
            <Badge className={cn('text-xs', complexityInfo.color)}>
              {complexityInfo.label}
            </Badge>
            {query.tags.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          {/* Parameters */}
          {query.parameters && query.parameters.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Parameters</h4>
              {query.parameters.map((param) => (
                <div key={param.name} className="space-y-1">
                  <Label className="text-xs">
                    {param.name}{' '}
                    {param.required && <span className="text-red-500">*</span>}
                  </Label>
                  <Input
                    placeholder={param.description}
                    value={
                      parameterValues[query.id]?.[param.name] ||
                      param.defaultValue ||
                      ''
                    }
                    onChange={(e) =>
                      updateParameterValue(query.id, param.name, e.target.value)
                    }
                    className="h-8 text-xs"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={() => handleSelectQuery(query)}
              variant="outline"
              size="sm"
              className="flex-1 flex items-center gap-2"
            >
              <Eye className="w-3 h-3" />
              Load
            </Button>
            <Button
              onClick={() => handleExecuteQuery(query)}
              size="sm"
              className="flex-1 flex items-center gap-2"
            >
              <Play className="w-3 h-3" />
              Execute
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Query Library
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search queries..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
            </div>

            <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                {Object.entries(categoryConfig).map(([key, config]) => (
                  <TabsTrigger key={key} value={key}>
                    {config.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>

            <Tabs
              value={selectedComplexity}
              onValueChange={setSelectedComplexity}
            >
              <TabsList>
                <TabsTrigger value="all">All Levels</TabsTrigger>
                <TabsTrigger value="simple">Simple</TabsTrigger>
                <TabsTrigger value="intermediate">Intermediate</TabsTrigger>
                <TabsTrigger value="advanced">Advanced</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardContent>
      </Card>

      {/* Query Results */}
      <div className="space-y-6">
        {/* Favorites */}
        {favoriteQueries.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500 fill-current" />
              <h3 className="text-lg font-semibold">Favorite Queries</h3>
              <Badge variant="outline">{favoriteQueries.length}</Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {favoriteQueries.map(renderQueryCard)}
            </div>
          </div>
        )}

        {/* All Queries */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            <h3 className="text-lg font-semibold">
              {favoriteQueries.length > 0 ? 'Other Queries' : 'All Queries'}
            </h3>
            <Badge variant="outline">{otherQueries.length}</Badge>
          </div>

          {otherQueries.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Search className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Queries Found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your search terms or filters.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {otherQueries.map(renderQueryCard)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
