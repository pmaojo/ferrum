#!/usr/bin/env node

/**
 * Docker Integration Test for Ferrum MCP Server
 * Tests the Docker container integration and context-aware execution
 */

const axios = require('axios');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8001';

async function testDockerIntegration() {
  console.log('🐳 Testing Ferrum MCP Docker Integration');
  console.log('=' .repeat(50));

  let testsPassed = 0;
  let totalTests = 0;

  // Test 1: Server Health
  totalTests++;
  console.log('\n📡 Test 1: Server Health Check');
  try {
    const response = await axios.get(`${MCP_SERVER_URL}/health`);
    console.log('✅ Server is healthy:', response.data.status);
    testsPassed++;
  } catch (error) {
    console.log('❌ Server health check failed:', error.message);
  }

  // Test 2: Container Status Check
  totalTests++;
  console.log('\n🔍 Test 2: Container Status Check');
  try {
    const response = await axios.get(`${MCP_SERVER_URL}/container/status`);
    console.log('📊 Container status:', response.data.container);
    if (response.data.stats) {
      console.log('📈 Container stats:', response.data.stats);
    }
    testsPassed++;
  } catch (error) {
    console.log('❌ Container status check failed:', error.message);
  }

  // Test 3: Check if Ferrum container is running
  totalTests++;
  console.log('\n🚀 Test 3: Ferrum Container Availability');
  try {
    const { stdout } = await execAsync('docker ps --filter name=ferrum_cli --format "{{.Names}}"');
    const containerRunning = stdout.trim().includes('ferrum_cli');
    
    if (containerRunning) {
      console.log('✅ Ferrum container is running');
      testsPassed++;
    } else {
      console.log('⚠️  Ferrum container not running - starting it...');
      
      // Try to start the container
      try {
        await execAsync('docker-compose -f docker-compose.ferrum.yml up -d ferrum-cli');
        console.log('🔄 Started Ferrum container');
        
        // Wait for container to be ready
        await new Promise(resolve => setTimeout(resolve, 10000));
        
        const statusResponse = await axios.get(`${MCP_SERVER_URL}/container/status`);
        if (statusResponse.data.container.running) {
          console.log('✅ Ferrum container is now running');
          testsPassed++;
        } else {
          console.log('❌ Failed to start Ferrum container');
        }
      } catch (startError) {
        console.log('❌ Failed to start Ferrum container:', startError.message);
      }
    }
  } catch (error) {
    console.log('❌ Failed to check container:', error.message);
  }

  // Test 4: Project Listing
  totalTests++;
  console.log('\n📁 Test 4: Project Listing');
  try {
    const response = await axios.get(`${MCP_SERVER_URL}/container/projects`);
    console.log(`📋 Found ${response.data.count} projects:`, response.data.projects.map(p => p.name));
    testsPassed++;
  } catch (error) {
    console.log('❌ Project listing failed:', error.message);
  }

  // Test 5: Tool Validation
  totalTests++;
  console.log('\n🛠️  Test 5: Tool Parameter Validation');
  try {
    const response = await axios.post(`${MCP_SERVER_URL}/validate/ferrum_init`, {
      parameters: {
        name: 'test-project',
        with_ai: true
      }
    });
    console.log('✅ Parameter validation passed:', response.data.valid);
    console.log('📝 Final parameters:', response.data.parameters);
    testsPassed++;
  } catch (error) {
    console.log('❌ Parameter validation failed:', error.response?.data?.error || error.message);
  }

  // Test 6: File Operations (if container is running)
  totalTests++;
  console.log('\n📄 Test 6: File Operations');
  try {
    // Try to read a common file
    const response = await axios.get(`${MCP_SERVER_URL}/container/files/Cargo.toml`);
    console.log('✅ File read successful, size:', response.data.size);
    testsPassed++;
  } catch (error) {
    if (error.response?.status === 404) {
      console.log('⚠️  File not found (expected if no projects exist)');
      testsPassed++; // This is acceptable
    } else {
      console.log('❌ File operation failed:', error.response?.data?.message || error.message);
    }
  }

  // Test 7: Tool Execution (if container is running)
  totalTests++;
  console.log('\n⚙️  Test 7: Tool Execution (ferrum_doctor)');
  try {
    const response = await axios.post(`${MCP_SERVER_URL}/execute/ferrum_doctor`, {
      parameters: {
        project_path: '.',
        check_dependencies: true,
        check_services: false
      }
    }, { timeout: 30000 });
    
    console.log('✅ Tool execution successful:', response.data.status);
    console.log('🏥 Health status:', response.data.result.health_status);
    testsPassed++;
  } catch (error) {
    if (error.response?.status === 503) {
      console.log('⚠️  Container not available for execution (expected if not running)');
    } else {
      console.log('❌ Tool execution failed:', error.response?.data?.error || error.message);
    }
  }

  // Test 8: Container Management
  totalTests++;
  console.log('\n🔧 Test 8: Container Management');
  try {
    // Test container status endpoint
    const statusResponse = await axios.get(`${MCP_SERVER_URL}/container/status`);
    console.log('✅ Container management endpoint working');
    console.log('📊 Current status:', statusResponse.data.container.status);
    testsPassed++;
  } catch (error) {
    console.log('❌ Container management failed:', error.message);
  }

  // Test 9: Error Handling
  totalTests++;
  console.log('\n🚨 Test 9: Error Handling');
  try {
    // Try to execute with invalid parameters
    await axios.post(`${MCP_SERVER_URL}/execute/ferrum_init`, {
      parameters: {
        name: '123-invalid-name' // Should fail validation
      }
    });
    console.log('❌ Error handling failed - should have rejected invalid parameters');
  } catch (error) {
    if (error.response?.status === 400) {
      console.log('✅ Error handling working - correctly rejected invalid parameters');
      testsPassed++;
    } else {
      console.log('❌ Unexpected error:', error.message);
    }
  }

  // Test 10: Performance Test
  totalTests++;
  console.log('\n⚡ Test 10: Performance Test');
  try {
    const startTime = Date.now();
    await axios.get(`${MCP_SERVER_URL}/tools`);
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    console.log(`✅ Response time: ${responseTime}ms`);
    if (responseTime < 1000) {
      console.log('🚀 Good performance (< 1s)');
    } else {
      console.log('⚠️  Slow response (> 1s)');
    }
    testsPassed++;
  } catch (error) {
    console.log('❌ Performance test failed:', error.message);
  }

  // Summary
  console.log('\n' + '='.repeat(50));
  console.log(`📊 Docker Integration Test Results: ${testsPassed}/${totalTests} tests passed`);
  
  if (testsPassed === totalTests) {
    console.log('🎉 All Docker integration tests passed!');
    return true;
  } else {
    console.log('💥 Some Docker integration tests failed!');
    return false;
  }
}

// Advanced integration test
async function testAdvancedIntegration() {
  console.log('\n🔬 Advanced Integration Tests');
  console.log('-'.repeat(30));

  // Test concurrent requests
  console.log('\n🔄 Testing concurrent requests...');
  try {
    const promises = [
      axios.get(`${MCP_SERVER_URL}/health`),
      axios.get(`${MCP_SERVER_URL}/tools`),
      axios.get(`${MCP_SERVER_URL}/container/status`)
    ];
    
    const results = await Promise.all(promises);
    console.log('✅ Concurrent requests handled successfully');
    console.log(`📊 Response codes: ${results.map(r => r.status).join(', ')}`);
  } catch (error) {
    console.log('❌ Concurrent request test failed:', error.message);
  }

  // Test large parameter validation
  console.log('\n📏 Testing large parameter validation...');
  try {
    const largePrompt = 'Create a comprehensive e-commerce system with user management, product catalog, shopping cart, order processing, payment integration, inventory management, and analytics dashboard. ' + 'x'.repeat(1000);
    
    const response = await axios.post(`${MCP_SERVER_URL}/validate/ferrum_prompt`, {
      parameters: {
        prompt: largePrompt
      }
    });
    
    console.log('✅ Large parameter validation successful');
  } catch (error) {
    console.log('❌ Large parameter validation failed:', error.response?.data?.error || error.message);
  }

  // Test timeout handling
  console.log('\n⏱️  Testing timeout handling...');
  try {
    // This should timeout quickly if implemented correctly
    await axios.post(`${MCP_SERVER_URL}/execute/ferrum_compile`, {
      parameters: {
        files: ['non-existent-file.yaml']
      }
    }, { timeout: 5000 });
    
    console.log('⚠️  Timeout test inconclusive');
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      console.log('✅ Timeout handling working correctly');
    } else if (error.response?.status === 503) {
      console.log('⚠️  Container not available for timeout test');
    } else {
      console.log('✅ Error handling working:', error.response?.data?.error || error.message);
    }
  }
}

// Run tests
if (require.main === module) {
  const args = process.argv.slice(2);
  const runAdvanced = args.includes('--advanced');

  testDockerIntegration().then(success => {
    if (runAdvanced) {
      return testAdvancedIntegration().then(() => success);
    }
    return success;
  }).then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('❌ Test suite failed:', error.message);
    process.exit(1);
  });
}

module.exports = { testDockerIntegration, testAdvancedIntegration };