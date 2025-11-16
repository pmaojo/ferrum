import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import prettierConfig from 'eslint-config-prettier';
import importPlugin from 'eslint-plugin-import';
import prettierPlugin from 'eslint-plugin-prettier';
import unusedImportsPlugin from 'eslint-plugin-unused-imports';

const baseConfig = {
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    globals: {
      console: 'readonly',
      process: 'readonly',
      Buffer: 'readonly',
      __dirname: 'readonly',
      __filename: 'readonly',
      global: 'readonly',
      setTimeout: 'readonly',
      clearTimeout: 'readonly',
      setInterval: 'readonly',
      clearInterval: 'readonly',
      setImmediate: 'readonly',
      clearImmediate: 'readonly',
    },
  },
  plugins: {
    import: importPlugin,
    'unused-imports': unusedImportsPlugin,
    prettier: prettierPlugin,
  },
  rules: {
    ...js.configs.recommended.rules,
    ...prettierConfig.rules,

    // Unused code detection
    'unused-imports/no-unused-imports': 'error',
    'unused-imports/no-unused-vars': [
      'error',
      {
        vars: 'all',
        varsIgnorePattern: '^_',
        args: 'after-used',
        argsIgnorePattern: '^_',
      },
    ],

    // Code formatting
    'prettier/prettier': 'error',

    // Import management
    'import/no-unresolved': 'off', // TypeScript handles this
    'import/order': [
      'error',
      {
        groups: [
          'builtin',
          'external',
          'internal',
          'parent',
          'sibling',
          'index',
        ],
        'newlines-between': 'always',
        alphabetize: {
          order: 'asc',
          caseInsensitive: true,
        },
      },
    ],
    'import/no-duplicates': 'error',
    'import/first': 'error',
    'import/newline-after-import': 'error',
    'import/no-default-export': 'off', // Allow default exports

    // Code quality rules
    'no-console': 'warn',
    'no-debugger': 'error',
    'prefer-const': 'error',
    'no-var': 'error',
    'no-undef': 'off', // TypeScript handles this
    'no-empty': 'error',
    'no-empty-function': 'warn',
    'no-unreachable': 'error',
    'no-unused-expressions': 'error',
    'no-useless-return': 'error',
    'no-useless-concat': 'error',
    'no-duplicate-imports': 'error',

    // Modern JavaScript practices
    'object-shorthand': 'error',
    'prefer-arrow-callback': 'error',
    'prefer-template': 'error',
    'prefer-destructuring': ['error', { object: true, array: false }],
  },
  settings: {
    'import/resolver': {
      typescript: {
        alwaysTryTypes: true,
        project: './tsconfig.json',
      },
      node: {
        extensions: ['.js', '.jsx', '.ts', '.tsx'],
      },
    },
  },
};

const typeScriptConfig = {
  files: ['**/*.ts', '**/*.tsx'],
  languageOptions: {
    parser: tsParser,
    parserOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      project: ['./tsconfig.json', './tsconfig.server.json'],
      ecmaFeatures: {
        jsx: true,
      },
    },
    globals: {
      React: 'readonly',
      JSX: 'readonly',
    },
  },
  plugins: {
    '@typescript-eslint': tsPlugin,
    import: importPlugin,
    'unused-imports': unusedImportsPlugin,
    prettier: prettierPlugin,
  },
  rules: {
    ...baseConfig.rules,
    ...tsPlugin.configs.recommended.rules,
    ...tsPlugin.configs['recommended-requiring-type-checking'].rules,

    // TypeScript-specific unused variable handling
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        vars: 'all',
        varsIgnorePattern: '^_',
        args: 'after-used',
        argsIgnorePattern: '^_',
      },
    ],

    // Type safety rules
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unsafe-assignment': 'warn',
    '@typescript-eslint/no-unsafe-call': 'warn',
    '@typescript-eslint/no-unsafe-member-access': 'warn',
    '@typescript-eslint/no-unsafe-return': 'warn',
    '@typescript-eslint/prefer-as-const': 'error',
    '@typescript-eslint/no-non-null-assertion': 'warn',

    // Code quality
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error',
    '@typescript-eslint/no-unnecessary-type-assertion': 'error',
    '@typescript-eslint/no-empty-interface': 'error',
    '@typescript-eslint/consistent-type-imports': [
      'error',
      { prefer: 'type-imports' },
    ],

    // Override base rules that conflict with TypeScript
    'no-unused-vars': 'off',
    'no-undef': 'off',
    'prefer-const': 'error',
  },
};

const testConfig = {
  files: [
    '**/*.test.ts',
    '**/*.test.tsx',
    '**/__tests__/**/*',
    'test/**/*',
    'e2e/**/*',
  ],
  languageOptions: {
    parser: tsParser,
    parserOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    globals: {
      describe: 'readonly',
      it: 'readonly',
      test: 'readonly',
      expect: 'readonly',
      beforeAll: 'readonly',
      beforeEach: 'readonly',
      afterAll: 'readonly',
      afterEach: 'readonly',
      jest: 'readonly',
    },
  },
  plugins: {
    '@typescript-eslint': tsPlugin,
    prettier: prettierPlugin,
  },
  rules: {
    ...baseConfig.rules,
    ...tsPlugin.configs.recommended.rules,
    'no-console': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unsafe-assignment': 'off',
    '@typescript-eslint/no-unsafe-call': 'off',
    '@typescript-eslint/no-unsafe-member-access': 'off',
    '@typescript-eslint/no-unused-vars': 'off',
    'unused-imports/no-unused-vars': 'off',
  },
};

const scriptsConfig = {
  files: ['scripts/**/*.ts', '*.config.ts', '*.config.js'],
  languageOptions: {
    parser: tsParser,
    parserOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    globals: {
      process: 'readonly',
      __dirname: 'readonly',
      __filename: 'readonly',
      console: 'readonly',
    },
  },
  plugins: {
    '@typescript-eslint': tsPlugin,
    prettier: prettierPlugin,
  },
  rules: {
    ...baseConfig.rules,
    ...tsPlugin.configs.recommended.rules,
    'no-console': 'off',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-var-requires': 'off',
  },
};

export default [
  {
    ignores: [
      'dist/**',
      'build/**',
      'node_modules/**',
      'client/**',
      'client/src/components/OnboardingTGAInterface.tsx',
      'client/src/components/sidebar/LeftSidebar.tsx',
      'coverage/**',
      'logs/**',
      '*.min.js',
      '*.bundle.js',
    ],
  },
  {
    ...baseConfig,
    files: ['**/*.js', '**/*.jsx'],
  },
  typeScriptConfig,
  testConfig,
  scriptsConfig,
];
