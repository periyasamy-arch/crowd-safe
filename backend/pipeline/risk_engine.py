import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


RISK_THRESHOLDS = {
    "LOW":      (0,  35),
    "MEDIUM":   (35, 55),
    "HIGH":     (55, 65),
    "CRITICAL": (65, 100),
}

MAX_DENSITY_VALUE = 50


@dataclass
class ZoneRisk:
    camera_id:         str
    zone:              str
    person_count:      int
    density:           float
    speed_variance:    float
    direction_entropy: float
    risk_score:        float
    risk_level:        str
    density_class:     str   = "LOW"
    cnn_confidence:    float = 0.0


def compute_density(count: int, max_people: int = MAX_DENSITY_VALUE) -> float:
    return min(count / max(max_people, 1), 1.0)


def compute_speed_variance(tracks) -> float:
    if len(tracks) < 2:
        return 0.0
    speeds = [np.sqrt(t.velocity[0]**2 + t.velocity[1]**2) for t in tracks]
    return float(min(np.var(speeds) / 100.0, 1.0))


def compute_direction_entropy(tracks) -> float:
    if len(tracks) < 2:
        return 0.0
    angles = []
    for t in tracks:
        vx, vy = t.velocity
        if np.sqrt(vx**2 + vy**2) > 0.5:
            angles.append(np.arctan2(vy, vx))
    if len(angles) < 2:
        return 0.0
    bins = np.zeros(8)
    for a in angles:
        bins[int((a + np.pi) / (2 * np.pi) * 8) % 8] += 1
    total = bins.sum()
    if total == 0:
        return 0.0
    probs = bins[bins > 0] / total
    return float(-np.sum(probs * np.log2(probs)) / np.log2(8))


def compute_risk(density: float, speed_variance: float, direction_entropy: float) -> float:
    return round(min((0.4*density + 0.3*speed_variance + 0.3*direction_entropy) * 100, 100), 1)


def get_risk_level(score: float) -> str:
    for level, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "CRITICAL"


def analyze_zone(
    camera_id: str,
    zone: str,
    tracks: list,
    person_count: int = None,
    density_class: str = "LOW",
    cnn_confidence: float = 0.0,
    frame_w: int = 640,
    frame_h: int = 480,
) -> ZoneRisk:
    count     = person_count if person_count is not None else len(tracks)
    density   = compute_density(count)
    speed_var = compute_speed_variance(tracks)
    dir_entr  = compute_direction_entropy(tracks)
    score     = compute_risk(density, speed_var, dir_entr)
    level     = get_risk_level(score)

    return ZoneRisk(
        camera_id=camera_id,
        zone=zone,
        person_count=count,
        density=density,
        speed_variance=speed_var,
        direction_entropy=dir_entr,
        risk_score=score,
        risk_level=level,
        density_class=density_class,
        cnn_confidence=cnn_confidence,
    )


def compute_global_risk(zone_risks: List[ZoneRisk]) -> Tuple[float, str]:
    if not zone_risks:
        return 0.0, "LOW"
    scores = [z.risk_score for z in zone_risks]
    g = round(max(scores) * 0.6 + np.mean(scores) * 0.4, 1)
    return g, get_risk_level(g)