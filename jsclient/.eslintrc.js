module.exports = {
    env: {
        browser: true,
        commonjs: true,
        es6: true,
        node: true,
    },
    globals: {
    },
    extends: [
        'eslint:recommended',
        'plugin:react/recommended',
    ],
    parserOptions: {
        sourceType: 'module',
        ecmaVersion: 9,
        ecmaFeatures: {
            jsx: true
        }
    },
    rules: {
        'comma-dangle': ['error', 'always-multiline'],
        'linebreak-style': ['error', 'unix'],
        'semi': ['error', 'always'],
        'no-unused-vars': ['warn'],
        'no-console': 0,
        'rest-spread-spacing': ["error", "never"],
    },
    ignorePatterns: ['protobuf.js'],
};