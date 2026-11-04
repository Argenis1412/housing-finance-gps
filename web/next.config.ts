import type { NextConfig } from "next";

const config: NextConfig = {
  agentRules: false,
  poweredByHeader: false,
  async rewrites() {
    return [
      {source: "/api/v1/comparison/saved-simulations", destination: "http://127.0.0.1:8000/api/v1/comparison/saved-simulations"},
      {source: "/api/v1/comparison/saved-simulations/:id", destination: "http://127.0.0.1:8000/api/v1/comparison/saved-simulations/:id"},
      {source: "/api/v1/comparison/simulations", destination: "http://127.0.0.1:8000/api/v1/comparison/simulations"}];
  },
};
export default config;
