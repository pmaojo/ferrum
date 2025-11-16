/**
 * Debug Ferrum DSL Converter
 */

import {
  convertDslToGraph,
  validateYamlContent,
} from './shared/converters/ferrum-dsl-converter';

const simpleYaml = `
app:
  name: TestApp
  features:
    - auth
    - graphql

modules:
  users:
    entity:
      fields:
        email: string
        password: string
`;

console.log('Testing YAML validation...');
const validation = validateYamlContent(simpleYaml);
console.log('Validation result:', validation);

if (validation.valid) {
  console.log('YAML is valid, attempting conversion...');
  try {
    const graphData = convertDslToGraph(simpleYaml);
    console.log('Conversion successful!');
    console.log('Graph data:', JSON.stringify(graphData, null, 2));
  } catch (error) {
    console.error('Conversion failed:', error);
  }
} else {
  console.log('YAML validation failed:', validation.error);
}