# Week 4 Day 6 Review: DLQ Remediation, Worker Autoscaling & Cluster Quarantine

**Date:** 08 November 2026  
**Author:** Sri Khyathi (`@srikhyathi`)  
**PR Target:** `Kailash-18/OmniSight#26` (`khyathi` -> `main`)  

## 1. Executive Summary & Architectural Overview

Week 4 Day 6 introduces high-availability enterprise resilience subsystems to OmniSight backend:

- **Dead-Letter Queue (DLQ) Remediation Engine**: Implements poison-pill isolation, exponential backoff retries, and manual/automated replaying for failed visual analysis payloads.
- **Dynamic Visual Worker Pool Autoscaler**: Dynamically sizes worker thread/process allocations based on real-time visual job queue depth and p99 latency SLA margins, equipped with cooldown hysteresis to eliminate resource flapping.
- **Cluster Quarantine & Fault Isolation Hub**: Automatically detects malfunctioning or flapping visual nodes and isolates them into a sandbox quarantine zone while maintaining zero-downtime cluster processing.

## 2. Mathematical Formulations & Component Mechanics

### 2.1 Exponential Backoff Retry Formulation

Let $T_{\text{base}}$ be the initial backoff interval ($1.0\text{ s}$), $\gamma$ the multiplier ($\gamma = 2.0$), and $k$ the attempt count ($0 \le k < k_{\text{max}}$):

$$t_{\text{retry}}(k) = t_{\text{fail}} + T_{\text{base}} \cdot \gamma^k$$

If $k \ge k_{\text{max}}$, the record is permanently classified as a **poison-pill** and deferred for quarantine inspection.

### 2.2 Worker Pool Scaling & Hysteresis Dampening

Let $Q(t)$ be queue depth, $W(t)$ active worker count, and $\tau_{\text{cool}} = 15\text{ s}$:

$$W(t + 1) = \begin{cases} \min(W_{\text{max}}, W(t) + \lceil Q(t) / 5 \rceil), & \text{if } Q(t) \ge Q_{\text{thresh}} \text{ and } \Delta t > \tau_{\text{cool}} \\ \max(W_{\text{min}}, W(t) - 1), & \text{if } Q(t) \le Q_{\text{idle}} \text{ and } \text{CPU} < 30\% \\ W(t), & \text{otherwise} \end{cases}$$

