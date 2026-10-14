"""Severity lookup and triage bands from the versioned config tables."""

from ignis_wo.config import load_config


def severity_for(entity_type: str, severity_config: dict | None = None) -> int:
    """Longest matching class path wins, so FailedState beats plain UndesirableState."""
    config = severity_config or load_config("severity_v1")
    best_length = -1
    best_severity = 0
    for class_path, severity in config["classes"].items():
        matches = entity_type == class_path or entity_type.startswith(class_path + "/")
        if matches and len(class_path) > best_length:
            best_length = len(class_path)
            best_severity = severity
    return best_severity


def band_for(score: float, triage_config: dict | None = None) -> str:
    config = triage_config or load_config("triage_v1")
    for band in config["bands"]:
        if score >= band["minimum"]:
            return band["name"]
    return config["zero_band"]
