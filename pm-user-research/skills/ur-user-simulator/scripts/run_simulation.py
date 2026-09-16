#!/usr/bin/env python3
"""Run one isolated external-API survey task per persona file."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_responses import (  # noqa: E402
    parse_answer_markdown,
    parse_model_json,
    parse_persona,
    parse_persons_summary,
    parse_questionnaire,
    quality_markdown,
    resolve_persona_files,
    validate_answer_directory,
    working_answers_dir,
    write_answer_markdown,
)


PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "provider_type": "openai_compatible", "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY", "json_mode": True, "max_tokens_field": "max_tokens",
    },
    "zhipu": {
        "provider_type": "openai_compatible", "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZAI_API_KEY", "json_mode": True, "max_tokens_field": "max_tokens",
    },
    "kimi": {
        "provider_type": "openai_compatible", "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "MOONSHOT_API_KEY", "json_mode": True, "max_tokens_field": "max_tokens",
    },
    "qwen": {
        "provider_type": "openai_compatible", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY", "json_mode": True, "max_tokens_field": "max_tokens",
    },
    "minimax": {
        "provider_type": "openai_compatible", "base_url": "https://api.minimaxi.com/v1",
        "api_key_env": "MINIMAX_API_KEY", "json_mode": False,
        "max_tokens_field": "max_completion_tokens", "request_options": {"max_completion_tokens": 2048},
    },
    "openai": {
        "provider_type": "openai_responses", "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY", "include_temperature": False,
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    """Load the models-only YAML; full JSON remains available for local mock tests."""
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return load_json(path)
    models: dict[str, str] = {}
    in_models = False
    for line_number, source_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = source_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            if line.strip() != "models:":
                raise ValueError(f"简洁 YAML 第 {line_number} 行只允许顶层字段 models")
            in_models = True
            continue
        if not in_models or ":" not in line:
            raise ValueError(f"简洁 YAML 第 {line_number} 行格式错误")
        name, raw_value = line.strip().split(":", 1)
        name, raw_value = name.strip(), raw_value.strip()
        if name not in PROVIDER_PRESETS:
            raise ValueError(f"未知提供商 ID：{name}")
        if name in models:
            raise ValueError(f"提供商 ID 重复：{name}")
        if raw_value in {"", "null", "~", "''", '\"\"'}:
            model = ""
        elif raw_value.startswith("\""):
            model = json.loads(raw_value)
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            model = raw_value[1:-1]
        else:
            model = raw_value
        models[name] = str(model)
    if not in_models or not models:
        raise ValueError("简洁 YAML 必须包含 models 映射")
    return {
        "providers": [
            {
                "name": name,
                **preset,
                "model": models.get(name, ""),
                "enabled": True,
                "request_options": dict(preset.get("request_options") or {}),
                "extra_headers": {},
            }
            for name, preset in PROVIDER_PRESETS.items()
        ],
        "runtime": {},
    }


def provider_ready(provider: dict[str, Any]) -> tuple[bool, str | None]:
    if not provider.get("enabled", False):
        return False, "disabled"
    if provider.get("provider_type") == "mock":
        return True, None
    model = str(provider.get("model") or "")
    if not model or model.startswith("REPLACE_WITH_"):
        return False, "model ID has not been configured"
    env_name = provider.get("api_key_env")
    if not env_name or not os.environ.get(str(env_name)):
        return False, f"missing environment variable: {env_name}"
    if not provider.get("base_url"):
        return False, "missing base_url"
    return True, None


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_provider(provider: dict[str, Any], system_prompt: str, user_prompt: str,
                  runtime: dict[str, Any]) -> str:
    provider_type = provider.get("provider_type")
    if provider_type == "mock":
        raise RuntimeError("mock provider is handled locally")
    api_key = os.environ[str(provider["api_key_env"])]
    headers = {"Authorization": f"Bearer {api_key}"}
    headers.update({str(key): str(value) for key, value in (provider.get("extra_headers") or {}).items()})
    base = str(provider["base_url"]).rstrip("/")
    model = str(provider["model"])
    temperature = runtime.get("temperature", 0.7)
    max_tokens = int(runtime.get("max_output_tokens", 3000))
    timeout = int(runtime.get("timeout_seconds", 120))
    if provider_type == "openai_compatible":
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        payload[str(provider.get("max_tokens_field") or "max_tokens")] = max_tokens
        if provider.get("json_mode", True):
            payload["response_format"] = {"type": "json_object"}
        payload.update(provider.get("request_options") or {})
        data = post_json(str(provider.get("endpoint") or f"{base}/chat/completions"), headers, payload, timeout)
        return str(data["choices"][0]["message"]["content"])
    if provider_type == "openai_responses":
        payload = {
            "model": model,
            "instructions": system_prompt,
            "input": user_prompt,
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if provider.get("include_temperature", False):
            payload["temperature"] = temperature
        payload.update(provider.get("request_options") or {})
        data = post_json(str(provider.get("endpoint") or f"{base}/responses"), headers, payload, timeout)
        if data.get("output_text"):
            return str(data["output_text"])
        texts = [
            str(content.get("text", ""))
            for item in data.get("output", [])
            for content in item.get("content", [])
            if content.get("type") in {"output_text", "text"}
        ]
        if texts:
            return "".join(texts)
        raise ValueError("Responses API returned no text output")
    raise ValueError(f"unsupported provider_type: {provider_type}")


def build_prompt(questionnaire_text: str, persona_text: str) -> tuple[str, str]:
    template = (Path(__file__).resolve().parent.parent / "templates" / "survey_prompt.md").read_text(encoding="utf-8")
    user_prompt = template.replace("{{persona_text}}", persona_text)
    user_prompt = user_prompt.replace("{{questionnaire_markdown}}", questionnaire_text)
    system_prompt = (
        "这是合成用户研究测试。严格返回 JSON，不要使用 Markdown 代码块。"
        "只依据本请求中的问卷和单人画像作答，不得补造画像未支持的私人经历。"
    )
    return system_prompt, user_prompt


def mock_result(questions: list[dict[str, Any]]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    for question in questions:
        qtype = question.get("type")
        options = question.get("options") or []
        source_id = question.get("options_from_question_id")
        if source_id:
            source_value = answers.get(str(source_id))
            options = source_value if isinstance(source_value, list) else [source_value]
            options = [item for item in options if item not in (None, "")]
        if qtype == "single_choice" and options:
            answers[question["id"]] = options[0]
        elif qtype in {"multi_choice", "ranking"} and options:
            answers[question["id"]] = options[: min(len(options), int(question.get("max_choices") or 1))]
        elif qtype in {"likert_scale", "nps"}:
            answers[question["id"]] = int((question.get("scale") or {"min": 1})["min"])
        else:
            answers[question["id"]] = "合成测试回答"
    return {"answers": answers, "answer_notes": {}}


def execute_one(order: int, user_id: str, persona_path: Path, questionnaire_path: Path,
                output_path: Path, providers: list[dict[str, Any]], runtime: dict[str, Any],
                run_id: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
    if output_path.exists():
        try:
            existing = parse_answer_markdown(output_path, questions)
            if existing["headers"].get("用户ID") == user_id:
                return {"order": order, "user_id": user_id, "status": "completed", "reused": True,
                        "provider": existing["headers"].get("模型提供商"), "model": existing["headers"].get("实际模型")}
        except (OSError, ValueError):
            pass
    questionnaire_text = questionnaire_path.read_text(encoding="utf-8")
    persona_text = persona_path.read_text(encoding="utf-8")
    persona = parse_persona(persona_path, user_id)
    system_prompt, user_prompt = build_prompt(questionnaire_text, persona_text)
    retries = max(0, int(runtime.get("max_retries", 2)))
    errors: list[str] = []
    rotated = providers[order % len(providers):] + providers[:order % len(providers)]
    for provider in rotated:
        for attempt in range(retries + 1):
            try:
                if provider.get("provider_type") == "mock":
                    parsed = mock_result(questions)
                else:
                    parsed = parse_model_json(call_provider(provider, system_prompt, user_prompt, runtime))
                write_answer_markdown(
                    output_path,
                    run_id=run_id,
                    user_id=user_id,
                    persona=persona,
                    questionnaire_path=questionnaire_path,
                    provider=str(provider.get("name")),
                    model=str(provider.get("model")),
                    questions=questions,
                    result=parsed,
                )
                return {"order": order, "user_id": user_id, "status": "completed", "reused": False,
                        "provider": provider.get("name"), "model": provider.get("model"), "attempts": attempt + 1}
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
                errors.append(f"{provider.get('name')}#{attempt + 1}: {type(exc).__name__}: {exc}")
                if attempt < retries:
                    time.sleep(min(8, 2 ** attempt + random.random()))
    return {"order": order, "user_id": user_id, "status": "failed", "error": " | ".join(errors)}


def main() -> int:
    parser = argparse.ArgumentParser(description="使用配置的外部模型并行回答问卷")
    parser.add_argument("--questionnaire", type=Path, required=True)
    parser.add_argument("--persons-summary", type=Path, required=True)
    parser.add_argument("--persons-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--max-concurrency", type=int, default=5)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()
    try:
        questionnaire = args.questionnaire.resolve()
        persons_summary = args.persons_summary.resolve()
        persons_dir = args.persons_dir.resolve()
        questions = parse_questionnaire(questionnaire)
        _, user_ids = parse_persons_summary(persons_summary)
        persona_files = resolve_persona_files(persons_dir, user_ids)
        config = load_config(args.config.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    providers, skipped = [], []
    for provider in config.get("providers", []):
        ready, reason = provider_ready(provider)
        if ready:
            providers.append(provider)
        elif provider.get("enabled", False):
            skipped.append(f"{provider.get('name')}: {reason}")
    if not providers:
        print(json.dumps({"status": "fallback_current_model", "unavailable": skipped}, ensure_ascii=False, indent=2))
        return 3
    if any(provider.get("provider_type") == "mock" for provider in providers) and not all(provider.get("provider_type") == "mock" for provider in providers):
        parser.error("mock 不能与真实提供商混合运行")
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_answers_dir = working_answers_dir(run_id)
    temp_answers_dir.mkdir(parents=True, exist_ok=True)
    runtime = dict(config.get("runtime") or {})
    runtime["max_retries"] = args.max_retries
    assignments = [
        (index, user_id, persona_files[user_id], questionnaire, temp_answers_dir / f"{user_id}.md")
        for index, user_id in enumerate(user_ids)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = [
            executor.submit(execute_one, index, user_id, persona_path, questionnaire_path, output_path,
                            providers, runtime, run_id, questions)
            for index, user_id, persona_path, questionnaire_path, output_path in assignments
        ]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    failures = {item["user_id"]: item.get("error", "模型调用失败") for item in results if item["status"] == "failed"}
    quality = validate_answer_directory(questionnaire, persons_summary, persons_dir, temp_answers_dir, failures)
    quality_path = output_dir / f"quality_report_{run_id}.md"
    quality_path.write_text(quality_markdown(run_id, quality), encoding="utf-8")
    print(json.dumps({
        "status": "completed",
        "run_id": run_id,
        "working_answers_dir": str(temp_answers_dir),
        "quality_report": str(quality_path),
        "total": quality["total"],
        "completed": quality["completed"],
        "failed": quality["failed"],
        "data_integrity": quality["data_integrity"],
        "unavailable_models": skipped,
    }, ensure_ascii=False, indent=2))
    return 0 if quality["data_integrity"] in {"excellent", "good"} else 1


if __name__ == "__main__":
    sys.exit(main())
