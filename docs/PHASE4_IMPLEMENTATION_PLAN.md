# Phase 4 Implementation Plan: Observability & Debugging

**Branch:** feat/observability  
**Date:** 2026-06-08  
**Status:** In Progress  
**Timeline:** 3-4 hours  
**Expected Impact:** Better troubleshooting and debugging capabilities

---

## Overview

Phase 4 focuses on adding comprehensive observability features to the GCM Agent, enabling better debugging, performance monitoring, and troubleshooting. This phase does not directly improve performance but provides critical insights for optimization and issue resolution.

---

## Goals

1. **Structured Logging:** Add detailed reasoning logs for tool selection and execution
2. **Token Metrics:** Track and log token usage for cost optimization
3. **Performance Monitoring:** Measure and log operation timings
4. **Debugging Dashboard:** Optional UI for visualizing metrics and logs

---

## Phase 4 Tasks

### Task 1: Tool Selection Reasoning Logs ⏱️ 1 hour

**Objective:** Add structured logging to capture LLM reasoning during tool selection

**Files to Modify:**
- `gcm_agent/agent/gcm_agent.py`
- `gcm_agent/utils/logger.py`

**Implementation Details:**

1. **Add Reasoning Extraction in Agent** (`gcm_agent/agent/gcm_agent.py`)
   - Capture LLM's tool selection reasoning from agent state
   - Log reasoning before tool execution
   - Include: selected tool, reasoning text, confidence (if available)
   - Format: Structured JSON for easy parsing

2. **Enhance Logger** (`gcm_agent/utils/logger.py`)
   - Add `log_tool_selection()` method
   - Add `log_tool_execution()` method
   - Support structured logging (JSON format)
   - Include timestamps, session IDs, query context

**Example Log Output:**
```json
{
  "timestamp": "2026-06-08T21:43:00Z",
  "session_id": "abc123",
  "event": "tool_selection",
  "query": "list all keys",
  "selected_tool": "gcm_AssetInventoryService_FetchAllCryptoObjects",
  "reasoning": "User wants to list all keys. The FetchAllCryptoObjects tool with asset_category='key' is the most appropriate.",
  "alternatives_considered": ["list_keys", "search_keys"],
  "confidence": "high"
}
```

**Testing:**
- Unit test: Verify log structure and content
- Integration test: Run queries and verify reasoning captured
- Manual test: Review logs for clarity and usefulness

---

### Task 2: Token Usage Tracking ⏱️ 1 hour

**Objective:** Track and log token consumption for cost optimization

**Files to Modify:**
- `gcm_agent/agent/gcm_agent.py`
- `gcm_agent/utils/logger.py`
- `gcm_agent/config/config_manager.py` (add token tracking config)

**Implementation Details:**

1. **Token Counter** (`gcm_agent/agent/gcm_agent.py`)
   - Extract token usage from LLM response metadata
   - Track: prompt tokens, completion tokens, total tokens
   - Accumulate per session and per query
   - Calculate cost estimates (if pricing available)

2. **Token Metrics Logger** (`gcm_agent/utils/logger.py`)
   - Add `log_token_usage()` method
   - Log per-query and cumulative metrics
   - Support cost calculation (configurable pricing)

3. **Configuration** (`gcm_agent/config/config_manager.py`)
   - Add `TokenTrackingConfig` class
   - Fields: `enabled`, `log_per_query`, `log_cumulative`, `pricing_per_1k_tokens`
   - Default: enabled=True, log_per_query=True

**Example Log Output:**
```json
{
  "timestamp": "2026-06-08T21:43:00Z",
  "session_id": "abc123",
  "event": "token_usage",
  "query": "list all keys",
  "prompt_tokens": 1250,
  "completion_tokens": 180,
  "total_tokens": 1430,
  "cumulative_session_tokens": 5420,
  "estimated_cost_usd": 0.0143
}
```

**Testing:**
- Unit test: Verify token counting accuracy
- Integration test: Run queries and verify cumulative tracking
- Manual test: Compare with WatsonX dashboard metrics

---

### Task 3: Performance Monitoring ⏱️ 1 hour

**Objective:** Measure and log operation timings for performance analysis

**Files to Modify:**
- `gcm_agent/agent/gcm_agent.py`
- `gcm_agent/mcp/client.py`
- `gcm_agent/utils/logger.py`

**Implementation Details:**

1. **Timing Decorators** (`gcm_agent/utils/logger.py`)
   - Create `@timed_operation` decorator
   - Automatically log operation duration
   - Support nested timing (parent/child operations)

2. **Agent Timing** (`gcm_agent/agent/gcm_agent.py`)
   - Time: query processing, tool selection, tool execution, response generation
   - Log timing breakdown per query
   - Track: min, max, avg, p95, p99 latencies

3. **MCP Client Timing** (`gcm_agent/mcp/client.py`)
   - Already has timing in `execute_tool()` (Phase 3)
   - Enhance with: network latency, serialization time
   - Log slow operations (>5s threshold)

**Example Log Output:**
```json
{
  "timestamp": "2026-06-08T21:43:00Z",
  "session_id": "abc123",
  "event": "performance_metrics",
  "query": "list all keys",
  "timings": {
    "total_duration_ms": 2340,
    "tool_selection_ms": 450,
    "tool_execution_ms": 1680,
    "response_generation_ms": 210
  },
  "tool_execution_breakdown": {
    "network_latency_ms": 120,
    "server_processing_ms": 1450,
    "serialization_ms": 110
  }
}
```

**Testing:**
- Unit test: Verify timing accuracy (±10ms tolerance)
- Integration test: Run queries and verify timing breakdown
- Load test: Verify performance under concurrent requests

---

### Task 4: Debugging Dashboard (Optional) ⏱️ 1-2 hours

**Objective:** Create Gradio UI tab for visualizing metrics and logs

**Files to Create:**
- `gcm_agent/ui/debug_ui.py` (NEW)

**Files to Modify:**
- `app.py` (add debug tab)

**Implementation Details:**

1. **Debug Dashboard UI** (`gcm_agent/ui/debug_ui.py`)
   - Tab 1: Real-time logs (last 100 entries)
   - Tab 2: Token usage metrics (charts)
   - Tab 3: Performance metrics (latency charts)
   - Tab 4: Tool analytics (from Phase 3)
   - Tab 5: Session history

2. **Metrics Visualization**
   - Use Gradio components: `gr.DataFrame`, `gr.Plot`, `gr.JSON`
   - Real-time updates (refresh every 5s)
   - Filters: by session, by time range, by event type

3. **Integration** (`app.py`)
   - Add "Debug" tab to main Gradio interface
   - Load debug UI conditionally (config flag)
   - Protect with authentication (optional)

**Example UI Layout:**
```
┌─────────────────────────────────────────┐
│ Debug Dashboard                         │
├─────────────────────────────────────────┤
│ [Logs] [Tokens] [Performance] [Tools]   │
├─────────────────────────────────────────┤
│ Real-time Logs (Last 100)               │
│ ┌─────────────────────────────────────┐ │
│ │ 21:43:00 | tool_selection | ...     │ │
│ │ 21:43:01 | tool_execution | ...     │ │
│ │ 21:43:02 | token_usage | ...        │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Filters: [Session] [Time] [Event Type] │
└─────────────────────────────────────────┘
```

**Testing:**
- Manual test: Verify UI renders correctly
- Manual test: Verify real-time updates work
- Manual test: Verify filters work correctly

---

## Dependencies

### Required
- None (uses existing dependencies)

### Optional (for Dashboard)
- `plotly>=5.0.0` (for advanced charts)
- `pandas>=2.0.0` (for data manipulation)

---

## File Structure

```
gcm_agent/
├── agent/
│   └── gcm_agent.py          # Enhanced with reasoning logs, token tracking, timing
├── mcp/
│   └── client.py             # Enhanced timing metrics
├── utils/
│   └── logger.py             # New: structured logging, timing decorators
├── ui/
│   └── debug_ui.py           # NEW: debugging dashboard (optional)
└── config/
    └── config_manager.py     # New: TokenTrackingConfig

tests/
├── test_observability.py     # NEW: observability tests
└── test_debug_ui.py          # NEW: dashboard tests (optional)

docs/
└── PHASE4_COMPLETION_SUMMARY.md  # NEW: completion summary
```

---

## Testing Strategy

### Unit Tests (`tests/test_observability.py`)

```python
def test_tool_selection_logging():
    """Verify tool selection reasoning is logged correctly"""
    pass

def test_token_usage_tracking():
    """Verify token counting and cumulative tracking"""
    pass

def test_performance_timing():
    """Verify operation timing accuracy"""
    pass

def test_timing_decorator():
    """Verify @timed_operation decorator works"""
    pass
```

### Integration Tests

```python
def test_full_observability_workflow():
    """Run query and verify all observability features work"""
    # 1. Execute query
    # 2. Verify reasoning logged
    # 3. Verify tokens tracked
    # 4. Verify timings recorded
    # 5. Verify logs structured correctly
    pass
```

### Manual Testing

1. **Reasoning Logs:**
   - Run diverse queries
   - Review logs for clarity and completeness
   - Verify reasoning matches actual tool selection

2. **Token Tracking:**
   - Run queries of varying complexity
   - Compare token counts with WatsonX dashboard
   - Verify cumulative tracking across session

3. **Performance Metrics:**
   - Run queries and check timing breakdown
   - Identify slow operations (>5s)
   - Verify timing accuracy with external timer

4. **Debug Dashboard (if implemented):**
   - Open dashboard and verify all tabs render
   - Run queries and verify real-time updates
   - Test filters and data export

---

## Success Criteria

### Functional Requirements
- ✅ Tool selection reasoning logged for every query
- ✅ Token usage tracked per query and cumulatively
- ✅ Operation timings recorded with <10ms overhead
- ✅ Logs structured in JSON format for easy parsing
- ✅ Debug dashboard displays metrics correctly (if implemented)

### Performance Requirements
- ✅ Logging overhead <5ms per operation
- ✅ No memory leaks from log accumulation
- ✅ Log file size manageable (<100MB per day)
- ✅ Dashboard updates without blocking agent

### Quality Requirements
- ✅ 90%+ test coverage for new code
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ Manual testing shows useful insights

---

## Implementation Order

### Day 1 (3-4 hours)
1. **Hour 1:** Implement tool selection reasoning logs
   - Modify `gcm_agent.py` to capture reasoning
   - Enhance `logger.py` with structured logging
   - Write unit tests

2. **Hour 2:** Implement token usage tracking
   - Add token counter to `gcm_agent.py`
   - Add token metrics logger
   - Add configuration
   - Write unit tests

3. **Hour 3:** Implement performance monitoring
   - Create timing decorators
   - Add timing to agent and MCP client
   - Write unit tests

4. **Hour 4 (Optional):** Create debugging dashboard
   - Create `debug_ui.py`
   - Integrate with `app.py`
   - Manual testing

---

## Rollback Plan

If issues arise:

```bash
# Revert to main
git checkout main
git pull

# Or revert specific commits
git revert <phase4-commit-hash>
```

**Rollback is safe:** Observability features are additive and non-breaking. Disabling logging simply returns to baseline behavior.

---

## Monitoring After Merge

### Metrics to Track
1. Log file size growth rate
2. Logging overhead impact on latency
3. Token tracking accuracy vs. WatsonX dashboard
4. Dashboard performance (if implemented)
5. User feedback on debugging usefulness

### Success Criteria
- Zero observability-related errors in first week
- Logging overhead <5ms per operation
- Log files <100MB per day
- Token tracking accuracy >95%
- User feedback positive (debugging easier)

---

## Documentation Updates

### Files to Update
1. `CHANGELOG.md` - Document Phase 4 changes
2. `AGENTS.md` - Add observability section
3. `docs/USER_GUIDE.md` - Add debugging guide
4. `docs/TROUBLESHOOTING.md` - Reference new logs
5. `README.md` - Mention observability features

### New Documentation
1. `docs/PHASE4_COMPLETION_SUMMARY.md` - Completion summary
2. `docs/OBSERVABILITY_GUIDE.md` - How to use observability features
3. `docs/DEBUG_DASHBOARD_GUIDE.md` - Dashboard usage (if implemented)

---

## Pull Request Template

```markdown
## Phase 4: Observability & Debugging

### Summary
Implements comprehensive observability features including structured logging, token tracking, performance monitoring, and optional debugging dashboard.

### Changes
- Added tool selection reasoning logs with structured JSON format
- Implemented token usage tracking per query and cumulatively
- Added performance monitoring with timing decorators
- Created optional debugging dashboard for metrics visualization
- Enhanced logger with structured logging capabilities

### Expected Impact
- Better troubleshooting and debugging capabilities
- Visibility into token usage for cost optimization
- Performance insights for optimization opportunities
- Easier issue diagnosis and resolution

### Testing
- ✅ Unit tests: 90%+ coverage
- ✅ Integration tests: Full workflow validated
- ✅ Manual testing: Logs and metrics verified
- ✅ Dashboard testing: UI renders and updates correctly (if implemented)

### Documentation
- docs/PHASE4_COMPLETION_SUMMARY.md
- docs/OBSERVABILITY_GUIDE.md
- CHANGELOG.md updated
- AGENTS.md updated

### Refs
- Implementation Plan: docs/PHASE4_IMPLEMENTATION_PLAN.md
- Phase 3 Summary: docs/PHASE3_COMPLETION_SUMMARY.md
```

---

## Next Steps After Phase 4

### Immediate
1. Merge Phase 4 to main
2. Monitor observability features in production
3. Gather user feedback on debugging usefulness

### Future Enhancements
1. **Advanced Analytics:** ML-based anomaly detection
2. **Alerting:** Automated alerts for errors/slow operations
3. **Distributed Tracing:** OpenTelemetry integration
4. **Cost Optimization:** Automated token usage optimization
5. **A/B Testing:** Compare different LLM configurations

---

## Contact

For questions or issues:
- Review docs/PHASE4_IMPLEMENTATION_PLAN.md
- Check docs/PHASE4_COMPLETION_SUMMARY.md (after completion)
- Review commit history for detailed changes

---

**Status:** 📋 Phase 4 Plan Complete - Ready for Implementation