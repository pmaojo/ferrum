export const nextjsAppRouterTemplate = {
  id: 'nextjs-app-router',
  name: 'Next.js App Router',
  description: 'Next.js application using the App Router architecture with modern React patterns',
  metadata: {
    layers: {
      app: ['page', 'layout', 'loading', 'error', 'not-found'],
      components: ['component', 'ui'],
      lib: ['utility', 'hook', 'context'],
      api: ['route', 'middleware'],
    },
    bestPractices: [
      'Use Server Components by default',
      'Implement proper loading and error boundaries',
      'Follow Next.js file-based routing conventions',
      'Optimize for performance with proper caching',
    ],
  },
  nodeTypes: [
    {
      type: 'page',
      pattern: 'app/(.*)/page\\.(tsx?|jsx?)$',
      color: '#0070f3',
      icon: '📄',
    },
    {
      type: 'layout',
      pattern: 'app/(.*)/layout\\.(tsx?|jsx?)$',
      color: '#7c3aed',
      icon: '🏗️',
    },
    {
      type: 'loading',
      pattern: 'app/(.*)/loading\\.(tsx?|jsx?)$',
      color: '#f59e0b',
      icon: '⏳',
    },
    {
      type: 'error',
      pattern: 'app/(.*)/error\\.(tsx?|jsx?)$',
      color: '#ef4444',
      icon: '❌',
    },
    {
      type: 'route',
      pattern: 'app/api/(.*)/route\\.(ts|js)$',
      color: '#10b981',
      icon: '🔗',
    },
    {
      type: 'component',
      pattern: 'components/(.*)\\.tsx?$',
      color: '#06b6d4',
      icon: '🧩',
    },
  ],
  validationRules: [
    {
      rule: 'page-layout-relationship',
      type: 'required' as const,
      description: 'Pages should have corresponding layouts when needed',
    },
    {
      rule: 'api-route-structure',
      type: 'required' as const,
      description: 'API routes should follow proper naming conventions',
    },
  ],
};