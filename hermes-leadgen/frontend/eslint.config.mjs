import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  ...nextCoreWebVitals,
  {
    ignores: [".next/**", "node_modules/**"],
  },
  {
    // MVP pages fetch data with plain useEffect + useState (no SWR/React Query
    // dependency yet — see docs/ROADMAP.md). That's exactly the pattern
    // react-hooks/set-state-in-effect flags; every occurrence here is the
    // intended initial-data-load call, not an accidental cascading update.
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default eslintConfig;
