# OmniSight Mid-Review Presentation Summary & Architecture Guide

> **Date**: 03 November 2026
> **Lead Engineer**: Sri Khyathi (Backend, Security & Release Automation)
> **Review Scope**: Weeks 1 & 2 Deliverables (287 Automated Tests Passing in Pytest)

## 1. Executive Summary
OmniSight is an autonomous multimodal visual QA agent designed to eliminate the fragility of traditional DOM-based UI testing.
The backend serves as the orchestration brain, integrating multimodal VLM analysis, zero-trust security boundaries, and automated GitHub PR workflows.

## 2. 10-Slide Deck Outline (`OmniSight_Mid_Review_Backend_Deck.pptx`):
- **Slide 1**: Title & Engineering Scope (Sri Khyathi, Member 1)
- **Slide 2**: Problem Statement (DOM Fragility vs Multimodal Vision QA)
- **Slide 3**: End-to-End System Architecture & Ownership Boundaries
- **Slide 4**: Week 1 Foundation (API Contracts, Pydantic Models, FastAPI ASGI Gateway)
- **Slide 5**: Week 2 Action Engine (AST-based JSON extraction, quote normalization)
- **Slide 6**: Week 2 Zero-Trust Security (Path traversal defense, style allowlist, CSS injection filters)
- **Slide 7**: Week 2 Retest Engine (Playwright sandbox evidence, visual diff scoring, timeline logs)
- **Slide 8**: Week 2 GitHub Automation (PyGithub PR creation, triage labels, webhook sync)
- **Slide 9**: Verification & Testing Matrix (287 passing tests, 100% pass rate in ~3s)
- **Slide 10**: Live Demo Flow & Evaluator Defense Strategy
