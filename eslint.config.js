export default [
  {
    files: ["dashboard/**/*.js"],
    languageOptions: { ecmaVersion: 2022, sourceType: "module", globals: { document: "readonly", fetch: "readonly", Intl: "readonly", echarts: "readonly" } },
    rules: { "no-undef": "error", "no-unused-vars": "error", "no-redeclare": "error" },
  },
];
