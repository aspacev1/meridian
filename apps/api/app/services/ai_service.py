"""AI incident naming, per ARCHITECTURE.md's "Incident naming prompt pattern".

Calls Claude with a JSON schema output constraint so the SLA monitor gets a
guaranteed-parseable {name, description} pair. Falls back to a deterministic
template when no API key is configured (local dev/test, or an org that
hasn't set one) so the SLA monitor still produces usable incidents offline.
"""

import json
from dataclasses import dataclass

import anthropic

from app.core.config import settings

_MODEL = "claude-opus-4-8"

_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Short incident title, e.g. 'Pipeline SLA Breach — dm_market'"},
        "description": {"type": "string", "description": "1-2 sentence technical description"},
    },
    "required": ["name", "description"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class IncidentNarrative:
    name: str
    description: str


def _fallback(mart_name: str, incident_type: str, delay_minutes: int | None, job_id: str) -> IncidentNarrative:
    label = "Pipeline SLA Breach" if incident_type == "pipeline_sla_breach" else "Data Quality Breach"
    name = f"{label} — {mart_name}"
    delay = f"+{delay_minutes}m overdue" if delay_minutes else "breach detected"
    description = f"{label} on {mart_name} ({delay}). Job {job_id or 'unknown'}."
    return IncidentNarrative(name=name, description=description)


def name_incident(
    mart_name: str,
    incident_type: str,
    layer_statuses: dict[str, str],
    delay_minutes: int | None,
    job_id: str,
) -> IncidentNarrative:
    if not settings.anthropic_api_key:
        return _fallback(mart_name, incident_type, delay_minutes, job_id)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"A data pipeline incident was detected.\n"
        f"Mart: {mart_name}\n"
        f"Incident type: {incident_type}\n"
        f"Layer statuses: {layer_statuses}\n"
        f"SLA delay (minutes): {delay_minutes}\n"
        f"Job ID: {job_id}\n\n"
        "Generate a short incident name and a 1-2 sentence technical description."
    )
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    parsed = json.loads(text)
    return IncidentNarrative(name=parsed["name"], description=parsed["description"])
