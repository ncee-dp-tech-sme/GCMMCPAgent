# Implementation Plan - LLM Stability Optimization

**Branch:** fix/llm-stability  
**Date:** 2026-06-08  
**Status:** In Progress

---

## Overview

This document outlines the phased approach for implementing stability and optimization improvements to the GCM Agent. The work is divided into 4 phases, with Phase 1 being the highest priority.

---

## Phase 1: Critical Fixes (Current Branch: fix/llm-stability)

**Timeline:** 2-3 hours  
**Expected Impact:** 70-80% improvement in reliability  
**Status:** In Progress

### Changes in This Phase

1. **Fix LLM Parameters** (15 min)
   - File: `gcm_agent/agent/gcm_agent.py` lines 133-138
   - Change: Optimize temperature, max_tokens, add decoding_method
   - Test: Run agent initialization, verify parameters applied

2. **Fix System Prompt Injection** (30 min)
   - File: `gcm_agent/agent/gcm_agent.py` lines 206-221
   - Change: Use `state_modifier` in `create_react_agent()`
   - Test: Verify system prompt appears once in logs

3. **Simplify Prompt** (20 min)
   - File: `gcm_agent/agent/prompts.py` lines 29-59
   - Change: Reduce to 10 lines, add concrete examples
   - Test: Read prompt, ensure clarity

4. **Add History Limiting** (20 min)
   - File: `gcm_agent/agent/gcm_agent.py` line 295
   - Change: Implement sliding window (20 messages)
   - Test: Verify history size stays bounded

### Testing Strategy

**Unit Tests:**
```bash
# Test LLM initialization
python -m pytest tests/test_agent.py::test_llm_initialization -v

# Test system prompt injection
python -m pytest tests/test_agent.py::test_system_prompt_injection -v

# Test history limiting
python -m pytest tests/test_agent.py::test_history_limiting -v
```

**Integration Tests:**
```bash
# Run full test suite
python -m pytest tests/ -v

# Manual testing with real queries
python test_agent_queries.py
```

**Test Queries:**
1. Simple: "List all keys"
2. Complex: "Show me all PQC certificates expiring in the next 30 days"
3. Multi-step: "Find all keys created by user admin and show their usage"
4. Long conversation: 15+ turns to test history limiting

### Success Criteria

- ✅ LLM parameters applied correctly (verify in logs)
- ✅ System prompt appears exactly once per conversation
- ✅ History never exceeds 20 messages
- ✅ Tool selection accuracy >90% on test queries
- ✅ Response completeness >95%
- ✅ No token limit errors on long conversations

### Merge Checklist

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing shows improvement
- [ ] Code reviewed (self-review minimum)
- [ ] CHANGELOG.md updated
- [ ] AGENTS.md updated with fixes applied
- [ ] Documentation updated

### Commit Message Template

```
fix: improve LLM stability and tool selection accuracy

Critical fixes for unreliable responses and wrong tool selection:

- Optimize LLM parameters (temp=0.1, max_tokens=4096, greedy decoding)
- Fix system prompt injection architecture (use state_modifier)
- Simplify parameter guidance in prompts (30 lines → 10 lines)
- Add history limiting (sliding window of 20 messages)

These changes address root causes identified in stability analysis:
- High temperature causing random tool selection
- Low max_tokens truncating reasoning
- Complex prompts overwhelming LLM
- Repeated system prompts wasting tokens

Expected impact: 70-80% improvement in reliability

Refs: docs/STABILITY_OPTIMIZATION_ANALYSIS.md
```

---

## Phase 2: Configuration & Resilience (Branch: feat/configurable-llm)

**Timeline:** 3-4 hours  
**Expected Impact:** 15-20% improvement in resilience  
**Status:** Not Started

### Changes in This Phase

1. **Make LLM Parameters Configurable**
   - Files: `gcm_agent/config/config_manager.py`, `gcm_agent/ui/config_ui.py`
   - Add: WatsonX parameter configuration (temperature, max_tokens, etc.)
   - Test: Change parameters via UI, verify applied

2. **Add Retry Logic**
   - Files: `gcm_agent/agent/gcm_agent.py`, `gcm_agent/mcp/client.py`
   - Add: Exponential backoff retry for tool execution
   - Test: Simulate network failures, verify retries

3. **Fix Recursion Limit Configuration**
   - File: `gcm_agent/agent/gcm_agent.py` line 208
   - Change: Pass max_iterations to create_react_agent()
   - Test: Verify limit applied at agent creation

### Dependencies

- Requires: tenacity library for retry logic
- Add to requirements.txt: `tenacity>=8.2.0`

### Testing Strategy

- Test parameter changes via UI
- Simulate network failures (disconnect MCP server)
- Test with different max_iterations values (5, 10, 20, 50)
- Verify retry backoff timing

---

## Phase 3: Tool Management (Branch: feat/intelligent-tool-selection)

**Timeline:** 4-6 hours  
**Expected Impact:** 5-10% improvement in tool selection  
**Status:** Not Started

### Design Decision Required

**Option A: Enable Discovery Mode by Default**
- Pros: Solves 128-tool limit, dynamic loading
- Cons: Slower initial response, requires working execute tool

**Option B: Implement Intelligent Tool Prioritization**
- Pros: Fast, works with current setup
- Cons: Requires maintenance, may miss edge cases

**Recommendation:** Option A (enable discovery mode) if execute tool bug is fixed, otherwise Option B

### Changes in This Phase

1. **Enable Discovery Mode OR Implement Prioritization**
   - Files: `gcm_agent/config/config_manager.py`, `gcm_agent/agent/gcm_agent.py`
   - Change: Based on design decision above
   - Test: Verify all required tools accessible

2. **Add Tool Usage Analytics**
   - File: `gcm_agent/mcp/tool_loader.py`
   - Add: Track which tools used, how often
   - Test: Verify analytics collected

3. **Improve Tool Caching**
   - File: `gcm_agent/mcp/tool_loader.py`
   - Add: Force refresh mechanism
   - Test: Verify cache refresh works

### Testing Strategy

- Test with queries requiring different tool categories
- Verify tool availability across diverse queries
- Test cache refresh mechanism
- Analyze tool usage patterns

---

## Phase 4: Observability (Branch: feat/observability)

**Timeline:** 3-4 hours  
**Expected Impact:** Better troubleshooting (no direct performance impact)  
**Status:** Not Started

### Changes in This Phase

1. **Add Tool Selection Reasoning Logs**
   - File: `gcm_agent/agent/gcm_agent.py`
   - Add: Structured logging for tool selection
   - Test: Verify logs contain reasoning

2. **Track Token Usage Metrics**
   - Files: `gcm_agent/agent/gcm_agent.py`, `gcm_agent/utils/logger.py`
   - Add: Token counting and logging
   - Test: Verify token counts accurate

3. **Add Performance Monitoring**
   - File: `gcm_agent/utils/logger.py`
   - Add: Timing metrics for operations
   - Test: Verify metrics collected

4. **Create Debugging Dashboard (Optional)**
   - New file: `gcm_agent/ui/debug_ui.py`
   - Add: Gradio tab for metrics visualization
   - Test: Verify dashboard displays correctly

### Dependencies

- May require: prometheus_client for metrics
- Optional: plotly for visualization

---

## Workflow Commands

### Phase 1 (Current)

```bash
# Already on branch
git status

# Make changes (see Phase 1 details above)

# Commit after each change
git add gcm_agent/agent/gcm_agent.py
git commit -m "fix: optimize LLM parameters for stability"

git add gcm_agent/agent/prompts.py
git commit -m "fix: simplify prompt to reduce LLM confusion"

# etc...

# Push branch
git push origin fix/llm-stability

# Create PR when ready
```

### Phase 2

```bash
# After Phase 1 merged to main
git checkout main
git pull
git checkout -b feat/configurable-llm

# Make changes...
# Test...
# Commit and push...
```

### Phase 3

```bash
git checkout main
git pull
git checkout -b feat/intelligent-tool-selection

# Make changes...
# Test...
# Commit and push...
```

### Phase 4

```bash
git checkout main
git pull
git checkout -b feat/observability

# Make changes...
# Test...
# Commit and push...
```

---

## Rollback Plan

If any phase causes issues:

```bash
# Revert to previous state
git checkout main
git pull

# Or revert specific commit
git revert <commit-hash>

# Or restore from backup tag
git checkout backup-before-optimization-20260608
```

---

## Documentation Updates

After each phase, update:

1. **CHANGELOG.md** - Add entry for changes
2. **AGENTS.md** - Update with fixes applied
3. **README.md** - Update if user-facing changes
4. **docs/USER_GUIDE.md** - Update if UI changes

---

## Communication Plan

### After Phase 1
- Update issue/ticket with results
- Share before/after metrics
- Get feedback on improvements

### After Phase 2
- Announce new configuration options
- Update user documentation
- Provide migration guide if needed

### After Phase 3
- Explain tool selection improvements
- Document any breaking changes
- Provide troubleshooting guide

### After Phase 4
- Share observability features
- Provide debugging guide
- Document metrics available

---

## Risk Mitigation

### Risks

1. **Breaking existing functionality**
   - Mitigation: Comprehensive testing, gradual rollout

2. **Performance regression**
   - Mitigation: Benchmark before/after, monitor metrics

3. **User confusion with new features**
   - Mitigation: Clear documentation, gradual feature introduction

4. **Merge conflicts**
   - Mitigation: Small, focused branches, frequent merges

### Contingency Plans

- Keep backup tags before each phase
- Maintain ability to quickly revert
- Have rollback procedure documented
- Test in staging environment first (if available)

---

## Success Metrics

### Phase 1 Targets
- Tool selection accuracy: 60% → 90%
- Response completeness: 70% → 95%
- Token usage: 3000 → 2000 per query
- Context overflow: Frequent → Rare

### Phase 2 Targets
- Configuration flexibility: 0 → 5 tunable parameters
- Retry success rate: 0% → 80% on transient failures
- User satisfaction: Baseline → +20%

### Phase 3 Targets
- Tool availability: 128 max → All tools accessible
- Tool selection time: Baseline → -30%
- Tool usage insights: None → Full analytics

### Phase 4 Targets
- Debugging time: Baseline → -50%
- Issue resolution: Baseline → +40% faster
- Observability coverage: 0% → 80%

---

## Timeline Summary

| Phase | Duration | Status | Branch |
|-------|----------|--------|--------|
| Phase 1 | 2-3 hours | In Progress | fix/llm-stability |
| Phase 2 | 3-4 hours | Not Started | feat/configurable-llm |
| Phase 3 | 4-6 hours | Not Started | feat/intelligent-tool-selection |
| Phase 4 | 3-4 hours | Not Started | feat/observability |
| **Total** | **12-17 hours** | | |

---

## Next Steps

1. ✅ Create branch (fix/llm-stability)
2. ✅ Document analysis and plan
3. ⏳ Implement Phase 1 changes
4. ⏳ Test Phase 1 changes
5. ⏳ Merge Phase 1 to main
6. ⏳ Begin Phase 2

**Current Focus:** Implementing Phase 1 changes