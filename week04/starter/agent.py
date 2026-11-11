"""The loop, the caps, and the tool executor. TODO 1 to 5.

Twenty lines of control flow and four decisions. Week 5 replaces this file
with about four lines of Pydantic AI, and the point of today is to know
exactly what those four lines are hiding.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from handbook import INJECTION_MARKER
from tools import SCHEMAS as ANTHROPIC_SCHEMAS
from tools import compute, search_services

from project.models import LARGE
from project.trace import TraceRecorder, local_conditions

# --------------------------------------------------------------------------
# TODO 1. The schemas, in the shape this endpoint speaks.
# --------------------------------------------------------------------------
#
# The descriptions in tools.py are already good and they are the actual
# lesson: each one says what the tool returns, when NOT to use it, and what
# an empty result means. A tool description is an interface contract whose
# audience is a model, so it is prompt engineering rather than documentation.
#
# What changes here is only the envelope. The local endpoint speaks the
# OpenAI wire format, which nests the schema under "function" and calls the
# parameter block "parameters". Other providers nest it differently and call
# it "input_schema". Nothing about your tool changes, which is the point:
# the envelope is plumbing and the description is the design.

def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap one Anthropic-shaped schema for the OpenAI wire format.

    The descriptions in tools.py are already written and they are the actual
    lesson: read them before you write this function. Each one says what the
    tool returns, when NOT to use it, and what an empty result means.

    All you do here is change the envelope. OpenAI nests the schema under a
    "function" key and calls the parameter block "parameters"; the shape in
    tools.py calls it "input_schema". Nothing about your tool changes, which
    is the point: the envelope is plumbing and the description is design.
    """
    return {"type": "function", "function": {
        "name": schema["name"], "description": schema["description"],
        "parameters": schema["input_schema"]}}


SCHEMAS = [to_openai_schema(s) for s in ANTHROPIC_SCHEMAS]
DISPATCH: dict[str, Callable[..., Any]] = {
    "search_services": search_services,
    "compute": compute,
}

# The list of concrete triggers on the search_services line is not
# decoration, and removing it costs four tasks. Without it the model
# decides from its own prior whether a commune handbook would plausibly
# contain the answer, and it is wrong about that surprisingly often, in
# the direction of refusing to look. Measured: 7/10 with the list, 3/10
# without it, same model and same everything else.
SYSTEM = """\
You answer questions for the help desk of Remerbaach, a Luxembourg commune, \
using the tools provided.

search_services  searches the commune handbook. Use it for any fee, opening \
time, form number, phone number, address, deadline, or procedure.
compute          evaluates one arithmetic expression.

How to work:
  1. Decide whether the question needs a fact from the handbook. If it does, \
you MUST call search_services before answering. You do not know what this \
handbook contains and you cannot tell from the question alone.
  2. You may only say the handbook does not cover something AFTER a search \
has come back without it. Saying it without searching is always wrong.
  3. If the answer needs arithmetic, call compute. Do not calculate in your \
head, even when it looks easy.
  4. If the question needs no handbook fact and no arithmetic, answer \
directly and call nothing at all.

Rules for the answer:
  Never state a fee, opening time, form number, or deadline that did not \
appear in a search result. Quote figures exactly as the handbook gives them.
  Answer in the language of the question, in under eighty words.
"""


# --------------------------------------------------------------------------
# The record of one run
# --------------------------------------------------------------------------

@dataclass
class Run:
    task_id: str
    answer: str = ""
    steps: int = 0
    tool_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0
    tokens: int = 0
    cap_fired: str | None = None
    saw_injection: bool = False       # did the hostile text reach the model
    tool_errors: int = 0

    @property
    def stopped_cleanly(self) -> bool:
        return self.cap_fired is None


# --------------------------------------------------------------------------
# TODO 5. Running the tools.
# --------------------------------------------------------------------------

MAX_RESULT_CHARS = 2000


def run_tool_call(name: str, raw_arguments: str) -> tuple[Any, bool]:
    """TODO 5. Validate, execute, catch, and cap. Four jobs, none the model's.

    Return (result, errored).

    1. The arguments arrive as a JSON string the model wrote. Parse them, and
       handle the case where it is not valid JSON, because sometimes it is
       not.
    2. The tool name is also something the model wrote. It can name a tool
       that does not exist. That is a real failure category, not an
       impossibility, so say so in a way the model can act on.
    3. Execute inside a try. An exception has to become a result the model
       can read rather than a crash, because the interesting question is
       what the agent does NEXT, and a traceback ends the run before you
       find out.
    4. Cap the size of what you return, in characters. A tool that returns
       half a megabyte should not blow up your context mid-run.

    One thing to get right that is not obvious. Do NOT put the exception's
    file path or stack into the result. A model handed a stack trace will
    paste it into its answer, and you have just told whoever asked the
    question what your directory layout is.
    """
    if name not in DISPATCH:
        return {"error": "Unknown tool. Available: search_services, compute."}, True
    try:
        args = json.loads(raw_arguments)
    except (ValueError, TypeError):
        return {"error": "Tool arguments must be valid JSON."}, True
    if not isinstance(args, dict):
        return {"error": "Tool arguments must be a JSON object."}, True
    schema = next(s for s in ANTHROPIC_SCHEMAS if s["name"] == name)["input_schema"]
    properties = schema["properties"]
    if any(field not in args for field in schema.get("required", [])) or set(args) - set(properties):
        return {"error": "Supply only the declared arguments and all required fields."}, True
    for field, value in args.items():
        rule = properties[field]
        if rule.get("type") == "string" and (not isinstance(value, str) or not value.strip()):
            return {"error": f"{field} must be a non-empty string."}, True
        if rule.get("type") == "integer":
            if type(value) is not int or not rule.get("minimum", value) <= value <= rule.get("maximum", value):
                return {"error": f"{field} must be an integer within the declared range."}, True
    try:
        result = DISPATCH[name](**args)
        encoded = json.dumps(result, ensure_ascii=False)
    except Exception:
        return {"error": "Tool execution failed; check the arguments and retry."}, True
    if len(encoded) > MAX_RESULT_CHARS:
        return encoded[: MAX_RESULT_CHARS - len("...[truncated]")] + "...[truncated]", False
    return result, False


# --------------------------------------------------------------------------
# TODO 2, 3, 4. The loop and its caps.
# --------------------------------------------------------------------------

def run_task(client, task, model: str = LARGE.name,
             max_steps: int = 6, stall_limit: int = 2,
             system: str = SYSTEM, week: int = 4,
             max_tokens_budget: int = 8000, no_tools: bool = False) -> Run:
    """TODO 2, 3, 4. The whole agent: a while loop with three exits.

    Build it in this order, and run it after each one.

    TODO 2, the loop itself. Call the model with `tools=SCHEMAS`. If the
      reply has no tool calls, the model is done: take its content as the
      answer and stop. Otherwise append the assistant turn, run each tool
      call, append one message per result with role "tool" and the matching
      tool_call_id, and go round again.

      Two mistakes that cost people ten minutes each. The assistant turn
      must be appended BEFORE the tool results, or the endpoint rejects a
      result that answers no request. And every tool result must carry the
      id of the call it answers.

    TODO 3, the step cap. `max_steps` iterations and then stop. When it
      fires, set `run.cap_fired` and produce a partial answer through
      `_partial` below. Never an empty string and never an exception.

    TODO 4, the no-progress detector. Track which doc_ids you have already
      seen. If a step brings back nothing new, that is one stall; if it
      happens `stall_limit` times in a row, stop.

      Defining progress is the design decision here and there is more than
      one defensible answer. "A document id I had not seen" is the one this
      solution uses because it is cheap, needs no model, and does not fire
      on a legitimate second search with different keywords, which naive
      "same call twice" detectors do. Say in DECISIONS.md what yours is.

    Fill in `run` as you go: steps, tool_calls, tokens, tool_errors, and
    `saw_injection` when the tool result contains handbook.INJECTION_MARKER.
    Record a trace with TraceRecorder exactly as weeks 1 to 3 did, one span
    per model call and one per tool call, because week 10 evaluates this.

    An agent without TODO 3 and TODO 4 is a program whose termination
    depends on a model's judgment, which is not a property you can promise
    anybody.
    """
    if min(max_steps, stall_limit, max_tokens_budget) < 1:
        raise ValueError("Safety limits must be positive")
    started = time.perf_counter()
    run = Run(task_id=task.id)
    recorder = TraceRecorder(
        week=week, case_id=task.id,
        conditions=local_conditions(model, temperature=0.0,
                                    max_steps=max_steps,
                                    stall_limit=stall_limit,
                                    max_tokens_budget=max_tokens_budget,
                                    no_tools=no_tools),
        user_input=task.question)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task.question}]
    seen_docs: set[str] = set()
    stalls = 0
    for _ in range(max_steps):
        params = {"model": model, "messages": messages,
                  "temperature": 0.0, "max_tokens": 400}
        if not no_tools:
            params["tools"] = SCHEMAS
        with recorder.step("model", model) as span:
            reply = client.chat.completions.create(**params)
            usage = getattr(reply, "usage", None)
            incoming = getattr(usage, "prompt_tokens", 0) or 0
            outgoing = getattr(usage, "completion_tokens", 0) or 0
            span.tokens(incoming, outgoing)
        run.tokens += incoming + outgoing
        run.steps += 1
        msg = reply.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            run.answer = msg.content or _partial(run, "The model returned no answer")
            if run.tokens >= max_tokens_budget:
                run.cap_fired = "budget"
                run.answer = _partial(run, "The budget cap fired")
            break
        if run.tokens >= max_tokens_budget:
            run.cap_fired = "budget"
            break
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [call.model_dump() for call in calls]})
        found_new: set[str] = set()
        for call in calls:
            name = call.function.name
            run.tool_calls.append(name)
            with recorder.step("tool", name) as span:
                result, errored = run_tool_call(name, call.function.arguments)
                span.detail(arguments=call.function.arguments, errored=errored)
            run.tool_errors += int(errored)
            found_new.update(_doc_ids(result) - seen_docs)
            content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            run.saw_injection |= INJECTION_MARKER in content
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": content})
        seen_docs.update(found_new)
        stalls = 0 if found_new else stalls + 1
        if stalls >= stall_limit:
            run.cap_fired = "no_progress"
            break
    else:
        run.cap_fired = "steps"
    if run.cap_fired:
        run.answer = _partial(run, f"The {run.cap_fired} cap fired")
    run.seconds = time.perf_counter() - started
    recorder.finish(output=run.answer,
                    outcome="degraded" if run.cap_fired else "ok",
                    cap_fired=run.cap_fired, tool_calls=run.tool_calls,
                    model_steps=run.steps, tool_errors=run.tool_errors)
    return run


def _partial(run: Run, reason: str) -> str:
    """What a capped run returns. Never an empty string, never a crash.

    A cap that returns nothing is indistinguishable from a system that had
    nothing to say, and week 8 spends a session on why that distinction
    matters. Say what happened and what was known so far.
    """
    return (f"I could not complete this. {reason}, after "
            f"{len(run.tool_calls)} tool call(s). Please telephone the help "
            f"desk on 4796-2222.")


def _doc_ids(tool_result: Any) -> set[str]:
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) \
            else tool_result
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {h.get("doc_id") for h in parsed
            if isinstance(h, dict) and h.get("doc_id")}
