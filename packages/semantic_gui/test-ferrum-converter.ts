/**
 * Test Ferrum DSL Converter
 */

import {
  convertDslToGraph,
  convertGraphToDsl,
  validateYamlContent,
  autoLayoutGraph,
} from './shared/converters/ferrum-dsl-converter';

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function runConverterTests() {
  console.log('🧪 Running Ferrum DSL Converter Tests...\n');

  // Test 1: Convert simple YAML DSL to graph
  console.log('Test 1: Convert simple YAML DSL to graph');
  
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
    usecases:
      createUser:
        input:
          - name: email
            type: string
          - name: password
            type: string
        output: User
    ports:
      UserRepository:
        methods:
          - name: save
            parameters:
              user: User
            returnType: User
    adapters:
      PostgresUserRepository:
        implements: UserRepository

iot:
  - name: blink
    protocol: gpio
    driver: rppal
    expose:
      method: POST
      path: /api/blink
  `;

  const graphData = convertDslToGraph(simpleYaml);
  
  assert(graphData.framework === 'ferrum', 'Framework should be ferrum');
  assert(graphData.metadata.app_name === 'TestApp', 'App name should be preserved');
  assert(graphData.metadata.features?.includes('auth'), 'Features should be preserved');
  assert(graphData.nodes.length > 0, 'Should have nodes');
  assert(graphData.edges.length > 0, 'Should have edges');
  
  // Check for specific node types
  const moduleNode = graphData.nodes.find(n => n.type === 'module');
  const entityNode = graphData.nodes.find(n => n.type === 'entity');
  const usecaseNode = graphData.nodes.find(n => n.type === 'usecase');
  const portNode = graphData.nodes.find(n => n.type === 'port');
  const adapterNode = graphData.nodes.find(n => n.type === 'adapter');
  const iotNode = graphData.nodes.find(n => n.type === 'iot');
  
  assert(moduleNode !== undefined, 'Should have module node');
  assert(entityNode !== undefined, 'Should have entity node');
  assert(usecaseNode !== undefined, 'Should have usecase node');
  assert(portNode !== undefined, 'Should have port node');
  assert(adapterNode !== undefined, 'Should have adapter node');
  assert(iotNode !== undefined, 'Should have IoT node');
  
  // Check IoT node data
  assert(iotNode!.data.protocol === 'gpio', 'IoT node should have correct protocol');
  assert(iotNode!.data.driver === 'rppal', 'IoT node should have correct driver');
  assert(iotNode!.data.expose?.method === 'POST', 'IoT node should have correct expose method');
  
  console.log('✅ YAML to graph conversion passed\n');

  // Test 2: Convert graph back to YAML DSL
  console.log('Test 2: Convert graph back to YAML DSL');
  
  const convertedYaml = convertGraphToDsl(graphData);
  assert(typeof convertedYaml === 'string', 'Converted YAML should be a string');
  assert(convertedYaml.includes('app:'), 'YAML should contain app section');
  assert(convertedYaml.includes('name: TestApp'), 'YAML should contain app name');
  assert(convertedYaml.includes('modules:'), 'YAML should contain modules section');
  assert(convertedYaml.includes('iot:'), 'YAML should contain IoT section');
  
  console.log('✅ Graph to YAML conversion passed\n');

  // Test 3: Round-trip conversion
  console.log('Test 3: Round-trip conversion (YAML -> Graph -> YAML)');
  
  const roundTripGraph = convertDslToGraph(convertedYaml);
  assert(roundTripGraph.framework === 'ferrum', 'Round-trip should preserve framework');
  assert(roundTripGraph.metadata.app_name === 'TestApp', 'Round-trip should preserve app name');
  
  const roundTripYaml = convertGraphToDsl(roundTripGraph);
  assert(roundTripYaml.includes('name: TestApp'), 'Round-trip YAML should preserve app name');
  
  console.log('✅ Round-trip conversion passed\n');

  // Test 4: Validate YAML content
  console.log('Test 4: Validate YAML content');
  
  const validationResult = validateYamlContent(simpleYaml);
  assert(validationResult.valid === true, 'Valid YAML should pass validation');
  
  const invalidYaml = `
app:
  # missing required name field
modules:
  invalid:
    # invalid structure
  `;
  
  const invalidValidation = validateYamlContent(invalidYaml);
  assert(invalidValidation.valid === false, 'Invalid YAML should fail validation');
  assert(invalidValidation.error !== undefined, 'Invalid YAML should have error message');
  
  console.log('✅ YAML validation passed\n');

  // Test 5: Auto-layout functionality
  console.log('Test 5: Auto-layout functionality');
  
  const layoutedGraph = autoLayoutGraph(graphData);
  assert(layoutedGraph.nodes.length === graphData.nodes.length, 'Layout should preserve all nodes');
  assert(layoutedGraph.edges.length === graphData.edges.length, 'Layout should preserve all edges');
  
  // Check that positions are reasonable
  const layoutModuleNode = layoutedGraph.nodes.find(n => n.type === 'module');
  assert(layoutModuleNode!.position.x >= 0, 'Module position X should be non-negative');
  assert(layoutModuleNode!.position.y >= 0, 'Module position Y should be non-negative');
  
  console.log('✅ Auto-layout functionality passed\n');

  // Test 6: Complex DSL with multiple modules
  console.log('Test 6: Complex DSL with multiple modules');
  
  const complexYaml = `
app:
  name: ComplexApp
  features:
    - auth
    - payments
    - notifications

modules:
  users:
    entity:
      fields:
        id: uuid
        email: string
        name: string
    usecases:
      registerUser:
        input:
          - name: email
            type: string
          - name: name
            type: string
        output: User
      authenticateUser:
        input:
          - name: email
            type: string
          - name: password
            type: string
        output: AuthToken
    ports:
      UserRepository:
        methods:
          - name: save
            parameters:
              user: User
            returnType: User
          - name: findByEmail
            parameters:
              email: string
            returnType: User
    adapters:
      PostgresUserRepository:
        implements: UserRepository

  payments:
    entity:
      fields:
        id: uuid
        amount: decimal
        currency: string
    usecases:
      processPayment:
        input:
          - name: amount
            type: decimal
          - name: currency
            type: string
        output: PaymentResult
    ports:
      PaymentGateway:
        methods:
          - name: charge
            parameters:
              amount: decimal
              currency: string
            returnType: PaymentResult
    adapters:
      StripePaymentGateway:
        implements: PaymentGateway

iot:
  - name: temperatureSensor
    protocol: mqtt
    expose:
      protocol: mqtt
      path: sensors/temperature
  - name: ledController
    protocol: gpio
    driver: rppal
    expose:
      method: POST
      path: /api/led/control
  `;

  const complexGraph = convertDslToGraph(complexYaml);
  
  // Should have multiple modules
  const moduleNodes = complexGraph.nodes.filter(n => n.type === 'module');
  assert(moduleNodes.length === 2, 'Should have 2 module nodes');
  
  // Should have multiple IoT components
  const iotNodes = complexGraph.nodes.filter(n => n.type === 'iot');
  assert(iotNodes.length === 2, 'Should have 2 IoT nodes');
  
  // Check that modules are positioned differently
  const usersModule = moduleNodes.find(n => n.data.fields?.name === 'users');
  const paymentsModule = moduleNodes.find(n => n.data.fields?.name === 'payments');
  assert(usersModule !== undefined, 'Should have users module');
  assert(paymentsModule !== undefined, 'Should have payments module');
  assert(
    usersModule!.position.x !== paymentsModule!.position.x || 
    usersModule!.position.y !== paymentsModule!.position.y,
    'Modules should have different positions'
  );
  
  console.log('✅ Complex DSL conversion passed\n');

  // Test 7: Error handling
  console.log('Test 7: Error handling');
  
  const malformedYaml = `
app:
  name: TestApp
modules:
  invalid:
    entity:
      fields: "this should be an object, not a string"
  `;

  try {
    convertDslToGraph(malformedYaml);
    assert(false, 'Should have thrown an error for malformed YAML');
  } catch (error) {
    assert(error instanceof Error, 'Should throw an Error instance');
    assert(error.message.includes('Invalid'), 'Error message should mention validation failure');
  }
  
  console.log('✅ Error handling passed\n');

  console.log('🎉 All DSL converter tests passed! Ferrum DSL conversion is working correctly.');
}

// Run the tests
try {
  runConverterTests();
} catch (error) {
  console.error('❌ Converter test failed:', error);
  process.exit(1);
}