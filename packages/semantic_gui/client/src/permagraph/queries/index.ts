export interface PredefinedQuery {
  id: string;
  name: string;
  description?: string;
  query: string;
}

export const predefinedQueries: PredefinedQuery[] = [
  {
    id: 'dependency-cycles',
    name: 'Dependency Cycles',
    description: 'Find modules that depend on each other forming a cycle',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
SELECT ?module ?dependency WHERE {
  ?module kth:dependsOnModule ?dependency .
  ?dependency kth:dependsOnModule ?module .
}`,
  },
  {
    id: 'impact-analysis',
    name: 'Impact Analysis',
    description: 'Find modules impacted by a dependency chain',
    query: `PREFIX kth: <http://kthulu.io/ontology#>
SELECT ?module ?impacted WHERE {
  ?module kth:dependsOnModule ?dependency .
  ?dependency kth:dependsOnModule* ?impacted .
}`,
  },
];
