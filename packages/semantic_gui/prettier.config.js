/** @type {import("prettier").Config} */
export default {
  // Basic formatting
  singleQuote: true,
  trailingComma: 'es5',
  semi: true,
  tabWidth: 2,
  useTabs: false,
  printWidth: 80,

  // Bracket and spacing
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'avoid',

  // JSX specific
  jsxSingleQuote: true,

  // End of line
  endOfLine: 'lf',

  // Plugin support for modern tooling
  plugins: [],

  // Override for specific file types
  overrides: [
    {
      files: '*.json',
      options: {
        tabWidth: 2,
      },
    },
    {
      files: '*.md',
      options: {
        printWidth: 100,
        proseWrap: 'preserve',
      },
    },
    {
      files: '*.yml',
      options: {
        tabWidth: 2,
        singleQuote: false,
      },
    },
  ],
};
