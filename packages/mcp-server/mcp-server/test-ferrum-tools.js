#!/usr/bin/env node

/**
 * Test script for Ferrum MCP tools
 * This script tests all Ferrum MCP tool definitions and parameter validation
 */

const axios = require('axios');

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8001';

// Test cases for each Ferrum tool
const TEST_CASES = {
  ferrum_init: [
    {
      name: 'valid-basic-project',
      parameters: {
        name: 'my-test-app'
      },
      shouldPass: true
    },
    {
      name: 'valid-full-featured-project',
      parameters: {
        name: 'full-featured-app',
        with_graph: true,
        with_ai: true,
        with_db: true,
        with_auth: true,
        frontend: 'react'
      },
      shouldPass: true
    },
    {
      name: 'invalid-missing-name',
      parameters: {},
      shouldPass: false
    },
    {
      name: 'invalid-bad-frontend',
      parameters: {
        name: 'test-app',
        frontend: 'invalid-framework'
      },
      shouldPass: false
    },
    {
      name: 'invalid-name-pattern',
      parameters: {
        name: '123-invalid-name'
      },
      shouldPass: false
    }
  ],

  ferrum_compile: [
    {
      name: 'valid-basic-compile',
      parameters: {
        files: ['gen/example.yaml']
      },
      shouldPass: true
    },
    {
      name: 'valid-advanced-compile',
      parameters: {
        files: ['gen/*.yaml'],
        output_dir: './output',
        module: 'auth',
        threads: 4,
        dry_run: true
      },
      shouldPass: true
    },
    {
      name: 'invalid-missing-files',
      parameters: {},
      shouldPass: false
    },
    {
      name: 'invalid-thread-count',
      parameters: {
        files: ['gen/test.yaml'],
        threads: 0
      },
      shouldPass: false
    }
  ],

  ferrum_prompt: [
    {
      name: 'valid-basic-prompt',
      parameters: {
        prompt: 'Create a user management system with authentication'
      },
      shouldPass: true
    },
    {
      name: 'valid-advanced-prompt',
      parameters: {
        prompt: 'Build an e-commerce API with products, orders, and payments',
        output_file: 'gen/ecommerce.yaml',
        context_project: './existing-project',
        use_patterns: true,
        ai_model: 'claude-3'
      },
      shouldPass: true
    },
    {
      name: 'invalid-short-prompt',
      parameters: {
        prompt: 'short'
      },
      shouldPass: false
    },
    {
      name: 'invalid-ai-model',
      parameters: {
        prompt: 'Create a user system',
        ai_model: 'invalid-model'
      },
      shouldPass: false
    }
  ],

  ferrum_doctor: [
    {
      name: 'valid-basic-doctor',
      parameters: {},
      shouldPass: true
    },
    {
      name: 'valid-advanced-doctor',
      parameters: {
        project_path: './my-project',
        check_dependencies: true,
        check_services: false,
        verbose: true
      },
      shouldPass: true
    }
  ],

  ferrum_dev: [
    {
      name: 'valid-basic-dev',
      parameters: {},
      shouldPass: true
    },
    {
      name: 'valid-custom-ports',
      parameters: {
        port: 8080,
        frontend_port: 3000,
        with_graph: true,
        with_ai: true
      },
      shouldPass: true
    },
    {
      name: 'invalid-port-range',
      parameters: {
        port: 80
      },
      shouldPass: false
    }
  ]
};

async function testMCPServer() {
  console.log('🧪 Testing Ferrum MCP Tools');
  console.log('=' .repeat(50));

  try {
    // Test server health
    console.log('\n📡 Testing server health...');
    const healthResponse = await axios.get(`${MCP_SERVER_URL}/health`);
    console.log('✅ Server is healthy:', healthResponse.data);

    // Test tools endpoint
    console.log('\n🔧 Testing tools endpoint...');
    const toolsResponse = await axios.get(`${MCP_SERVER_URL}/tools`);
    const tools = toolsResponse.data.tools;
    console.log(`✅ Found ${tools.length} tools:`, tools.map(t => t.name));

    // Test each tool's parameter validation
    let totalTests = 0;
    let passedTests = 0;

    for (const [toolName, testCases] of Object.entries(TEST_CASES)) {
      console.log(`\n🛠️  Testing tool: ${toolName}`);
      console.log('-'.repeat(30));

      // Get tool definition
      try {
        const toolResponse = await axios.get(`${MCP_SERVER_URL}/tools/${toolName}`);
        console.log(`📋 Tool definition loaded for ${toolName}`);
      } catch (error) {
        console.error(`❌ Failed to get tool definition for ${toolName}:`, error.message);
        continue;
      }

      // Test each case
      for (const testCase of testCases) {
        totalTests++;
        console.log(`\n  🧪 Test: ${testCase.name}`);
        console.log(`     Parameters:`, JSON.stringify(testCase.parameters, null, 2));

        try {
          const validateResponse = await axios.post(
            `${MCP_SERVER_URL}/validate/${toolName}`,
            { parameters: testCase.parameters }
          );

          if (testCase.shouldPass) {
            console.log(`     ✅ PASS - Validation succeeded as expected`);
            console.log(`     📝 Final parameters:`, JSON.stringify(validateResponse.data.parameters, null, 2));
            passedTests++;
          } else {
            console.log(`     ❌ FAIL - Expected validation to fail but it passed`);
          }
        } catch (error) {
          if (!testCase.shouldPass) {
            console.log(`     ✅ PASS - Validation failed as expected: ${error.response?.data?.error || error.message}`);
            passedTests++;
          } else {
            console.log(`     ❌ FAIL - Expected validation to pass but it failed: ${error.response?.data?.error || error.message}`);
          }
        }
      }
    }

    console.log('\n' + '='.repeat(50));
    console.log(`📊 Test Results: ${passedTests}/${totalTests} tests passed`);
    
    if (passedTests === totalTests) {
      console.log('🎉 All tests passed!');
      process.exit(0);
    } else {
      console.log('💥 Some tests failed!');
      process.exit(1);
    }

  } catch (error) {
    console.error('❌ Test suite failed:', error.message);
    process.exit(1);
  }
}

// Test tool execution examples (requires Ferrum container)
async function testToolExecution() {
  console.log('\n🚀 Testing tool execution (requires Ferrum container)...');
  
  const executionTests = [
    {
      tool: 'ferrum_doctor',
      parameters: {
        project_path: '.',
        check_dependencies: true,
        check_services: false
      }
    }
  ];

  for (const test of executionTests) {
    try {
      console.log(`\n🔧 Executing ${test.tool}...`);
      const response = await axios.post(
        `${MCP_SERVER_URL}/execute/${test.tool}`,
        { parameters: test.parameters },
        { timeout: 30000 }
      );
      
      console.log('✅ Execution successful:', response.data.status);
      console.log('📄 Result:', JSON.stringify(response.data.result, null, 2));
    } catch (error) {
      if (error.response?.status === 503) {
        console.log('⚠️  Ferrum container not available - skipping execution test');
      } else {
        console.log('❌ Execution failed:', error.response?.data?.error || error.message);
      }
    }
  }
}

// Run tests
if (require.main === module) {
  const args = process.argv.slice(2);
  const includeExecution = args.includes('--execution');

  testMCPServer().then(() => {
    if (includeExecution) {
      return testToolExecution();
    }
  });
}

module.exports = { testMCPServer, testToolExecution };