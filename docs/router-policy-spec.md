# Router & Policy Specification

## RouterRequest

```jsonc
{
  "query": "Explain why this order failed in MyLV.",
  "intent": {
    "task_type": "analysis",      // "qa" | "chat" | "code_assist" | ...
    "priority": "high",           // "low" | "normal" | "high"
    "latency_tolerance_ms": 3000
  },
  "environment": {
    "hardware_profile": {
      "device_type": "DESKTOP",   // "DESKTOP" | "LAPTOP" | "MOBILE"
      "class": "M1_MAX",
      "memory_gb": 32
    },
    "network_profile": {
      "status": "STABLE",         // "OFFLINE" | "UNSTABLE" | "STABLE"
      "rtt_ms": 45
    },
    "power_profile": "AC"         // "AC" | "BATTERY" | "LOW_POWER"
  },
  "policy": {
    "privacy_level": "STRICT",    // "STRICT" | "BALANCED" | "RELAXED"
    "cost_budget": {
      "mode": "PER_REQUEST",
      "limit_usd": 0.05
    },
    "allow_external_llm": false,
    "allow_cloud_routing": false,
    "max_compute_steps": 3
  }
}