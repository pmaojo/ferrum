import type { Template } from '@shared/schema';

export const nextjsAppRouterTemplate: Template = {
  id: 'nextjs-app-router',
  name: 'Next.js App Router',
  description:
    'Modern Next.js application with App Router, Server Components, and full-stack architecture',
  nodeTypes: [
    {
      type: 'page',
      pattern: 'app/(.*)/page\\.(tsx|ts|jsx|js)$',
      color: '#3b82f6',
      icon: 'fas fa-file-code',
    },
    {
      type: 'layout',
      pattern: 'app/(.*)/layout\\.(tsx|ts|jsx|js)$',
      color: '#8b5cf6',
      icon: 'fas fa-th-large',
    },
    {
      type: 'component',
      pattern: 'components/(.*)/.*\\.(tsx|ts|jsx|js)$',
      color: '#10b981',
      icon: 'fas fa-puzzle-piece',
    },
    {
      type: 'api-route',
      pattern: 'app/api/(.*)/route\\.(ts|js)$',
      color: '#f59e0b',
      icon: 'fas fa-exchange-alt',
    },
    {
      type: 'middleware',
      pattern: 'middleware\\.(ts|js)$',
      color: '#ef4444',
      icon: 'fas fa-filter',
    },
    {
      type: 'hook',
      pattern: 'hooks/(.*)/.*\\.(ts|tsx|js|jsx)$',
      color: '#06b6d4',
      icon: 'fas fa-anchor',
    },
    {
      type: 'server-action',
      pattern: 'app/(.*)/actions\\.(ts|js)$',
      color: '#84cc16',
      icon: 'fas fa-server',
    },
    {
      type: 'loading',
      pattern: 'app/(.*)/loading\\.(tsx|ts|jsx|js)$',
      color: '#6366f1',
      icon: 'fas fa-spinner',
    },
    {
      type: 'error',
      pattern: 'app/(.*)/error\\.(tsx|ts|jsx|js)$',
      color: '#dc2626',
      icon: 'fas fa-exclamation-triangle',
    },
    {
      type: 'not-found',
      pattern: 'app/(.*)/not-found\\.(tsx|ts|jsx|js)$',
      color: '#7c2d12',
      icon: 'fas fa-question-circle',
    },
    {
      type: 'global-error',
      pattern: 'app/global-error\\.(tsx|ts|jsx|js)$',
      color: '#991b1b',
      icon: 'fas fa-bomb',
    },
    {
      type: 'route-group',
      pattern: 'app/\\((.*)\\)/.*',
      color: '#059669',
      icon: 'fas fa-folder',
    },
    {
      type: 'lib',
      pattern: 'lib/(.*)/.*\\.(ts|tsx|js|jsx)$',
      color: '#7c3aed',
      icon: 'fas fa-tools',
    },
    {
      type: 'util',
      pattern: 'utils/(.*)/.*\\.(ts|tsx|js|jsx)$',
      color: '#0891b2',
      icon: 'fas fa-wrench',
    },
    {
      type: 'context',
      pattern: 'contexts?/(.*)/.*\\.(tsx|ts|jsx|js)$',
      color: '#c026d3',
      icon: 'fas fa-share-alt',
    },
    {
      type: 'provider',
      pattern: 'providers?/(.*)/.*\\.(tsx|ts|jsx|js)$',
      color: '#db2777',
      icon: 'fas fa-cloud',
    },
  ],
  validationRules: [
    {
      rule: 'page-requires-default-export',
      type: 'required',
      description: 'Page components must have a default export',
    },
    {
      rule: 'layout-requires-children',
      type: 'required',
      description: 'Layout components must accept and render children prop',
    },
    {
      rule: 'no-client-in-server-components',
      type: 'prohibited',
      description: 'Server components should not use client-side APIs',
    },
    {
      rule: 'api-route-proper-methods',
      type: 'required',
      description:
        'API routes should export proper HTTP method handlers (GET, POST, etc.)',
    },
    {
      rule: 'middleware-edge-runtime',
      type: 'required',
      description: 'Middleware should be optimized for Edge Runtime',
    },
    {
      rule: 'server-actions-async',
      type: 'required',
      description: 'Server Actions must be async functions',
    },
    {
      rule: 'no-nested-layouts-conflict',
      type: 'prohibited',
      description: 'Avoid conflicting nested layout patterns',
    },
    {
      rule: 'error-boundary-proper-structure',
      type: 'required',
      description: 'Error components must accept error and reset props',
    },
    {
      rule: 'loading-ui-immediate',
      type: 'required',
      description: 'Loading components should provide immediate feedback',
    },
    {
      rule: 'client-components-use-client',
      type: 'required',
      description: "Interactive components must have 'use client' directive",
    },
    {
      rule: 'no-circular-dependencies',
      type: 'prohibited',
      description: 'Circular dependencies between components are not allowed',
    },
    {
      rule: 'proper-import-structure',
      type: 'required',
      description: 'Follow Next.js import conventions and barrel exports',
    },
  ],
  universalTagSystem: {
    detection: {
      filePatterns: [],
      codePatterns: [],
      directoryPatterns: [],
    },
    extraction: {
      nativePatterns: {},
      conventions: {
        directoryMapping: {},
        fileNamePatterns: {},
        classNamePatterns: {},
      },
    },
    translation: {
      toSCG: {},
      fromSCG: {},
    },
    autoTagging: {
      enabled: false,
      confidence: 'low',
      patterns: [],
    },
  },
  metadata: {
    framework: 'Next.js',
    pattern: 'App Router Architecture',
    description:
      'Modern React framework with App Router, Server Components, and streaming',
    documentation: 'https://nextjs.org/docs/app',
    layers: [
      {
        name: 'App Layer',
        components: [
          'page',
          'layout',
          'loading',
          'error',
          'not-found',
          'global-error',
        ],
        description: 'Next.js App Router file conventions',
      },
      {
        name: 'API Layer',
        components: ['api-route', 'server-action', 'middleware'],
        description: 'Server-side logic and API endpoints',
      },
      {
        name: 'Component Layer',
        components: ['component', 'hook', 'context', 'provider'],
        description: 'Reusable UI components and state management',
      },
      {
        name: 'Utility Layer',
        components: ['lib', 'util'],
        description: 'Shared utilities and helper functions',
      },
    ],
    bestPractices: [
      'Use Server Components by default, Client Components when needed',
      'Implement proper error boundaries at route level',
      'Optimize loading states with streaming',
      'Follow App Router file conventions',
      'Use Server Actions for form handling',
      'Implement proper TypeScript types',
      'Optimize bundle size with dynamic imports',
      'Use middleware for authentication and redirects',
    ],
  },
};
