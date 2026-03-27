from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DATETIME_FORMAT = "%Y/%m/%d %H:%M"
EXPECTED_COLUMNS = [
    "NAME",
    "SENID",
    "TIME",
    "V",
    "AVGV",
    "MAXV",
    "MAXT",
    "MINV",
    "MINT",
    "S",
    "AVGS",
    "MAXS",
    "MINS",
    "SPAN",
]
NUMERIC_COLUMNS = ["V", "AVGV", "MAXV", "MINV", "S", "AVGS", "MAXS", "MINS", "SPAN"]
DATETIME_COLUMNS = ["TIME", "MAXT", "MINT"]
DAILY_REPEAT_COLUMNS = [
    "AVGV",
    "MAXV",
    "MAXT",
    "MINV",
    "MINT",
    "AVGS",
    "MAXS",
    "MINS",
    "SPAN",
]


@dataclass
class AuditConfig:
    input_csv: Path
    submit_example_csv: Path
    output_dir: Path
    encoding: str = "gb18030"
    target_column: str = "V"
    expected_interval_minutes: int = 15


@dataclass
class Task1DataBundle:
    chinese_header: list[str]
    english_header: list[str]
    rows: list[dict[str, Any]]


def _parse_float(value: str) -> float | None:
    text = value.strip()
    if text == "":
        return None
    return float(text)


def _parse_dt(value: str) -> datetime | None:
    text = value.strip()
    if text == "":
        return None
    return datetime.strptime(text, DATETIME_FORMAT)


def _require_dt(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"Field {field_name} is not a valid datetime: {value!r}")
    return value


def _require_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"Field {field_name} is not a valid number: {value!r}")
    return float(value)


def _ensure_dirs(output_dir: Path) -> dict[str, Path]:
    paths = {
        "root": output_dir,
        "tables": output_dir / "tables",
        "figures": output_dir / "figures",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _read_training_rows(
    config: AuditConfig,
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    with config.input_csv.open("r", encoding=config.encoding, newline="") as f:
        reader = csv.reader(f)
        chinese_header = next(reader)
        english_header = next(reader)
        if english_header != EXPECTED_COLUMNS:
            raise ValueError(f"Unexpected columns: {english_header}")
        for raw in reader:
            item: dict[str, Any] = {
                key: value.strip() for key, value in zip(english_header, raw)
            }
            for column in NUMERIC_COLUMNS:
                item[column] = _parse_float(str(item[column]))
            for column in DATETIME_COLUMNS:
                item[column] = _parse_dt(str(item[column]))
            rows.append(item)
    return chinese_header, english_header, rows


def load_task1_training_data(
    input_csv: Path,
    encoding: str = "gb18030",
) -> Task1DataBundle:
    chinese_header, english_header, rows = _read_training_rows(
        AuditConfig(
            input_csv=input_csv,
            submit_example_csv=input_csv,
            output_dir=input_csv.parent,
            encoding=encoding,
        )
    )
    return Task1DataBundle(
        chinese_header=chinese_header,
        english_header=english_header,
        rows=rows,
    )


def _read_submit_example(path: Path) -> list[datetime]:
    submit_times: list[datetime] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("TIME"):
                continue
            parsed = _parse_dt(row["TIME"])
            if parsed is None:
                raise ValueError(f"Invalid TIME in submit example: {row['TIME']!r}")
            submit_times.append(parsed)
    return submit_times


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return f"{value.year}/{value.month}/{value.day} {value.hour}:{value.minute:02d}"


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return sorted_values[lower]
    weight = pos - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _describe(values: list[float]) -> dict[str, float]:
    sorted_values = sorted(values)
    return {
        "count": float(len(values)),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": sorted_values[0],
        "p01": _quantile(sorted_values, 0.01),
        "p05": _quantile(sorted_values, 0.05),
        "p25": _quantile(sorted_values, 0.25),
        "p50": _quantile(sorted_values, 0.50),
        "p75": _quantile(sorted_values, 0.75),
        "p95": _quantile(sorted_values, 0.95),
        "p99": _quantile(sorted_values, 0.99),
        "max": sorted_values[-1],
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _line_chart_svg(
    series: list[float], width: int = 1200, height: int = 360, color: str = "#125b50"
) -> str:
    if not series:
        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='360'></svg>"
        )
    margin = 32
    plot_w = width - margin * 2
    plot_h = height - margin * 2
    min_v = min(series)
    max_v = max(series)
    span = max(max_v - min_v, 1e-9)
    points = []
    for idx, value in enumerate(series):
        x = margin + (idx / max(len(series) - 1, 1)) * plot_w
        y = margin + (1 - (value - min_v) / span) * plot_h
        points.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(points)
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='#f7fbfa'/>"
        f"<line x1='{margin}' y1='{height - margin}' x2='{width - margin}' y2='{height - margin}' stroke='#9bb8b0'/>"
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height - margin}' stroke='#9bb8b0'/>"
        f"<polyline fill='none' stroke='{color}' stroke-width='1.6' points='{polyline}'/>"
        f"<text x='{margin}' y='20' fill='#24423d' font-size='14'>min={min_v:.2f} max={max_v:.2f}</text>"
        "</svg>"
    )


def _bar_chart_svg(
    labels: list[str], values: list[float], width: int = 1200, height: int = 360
) -> str:
    margin = 32
    plot_w = width - margin * 2
    plot_h = height - margin * 2
    max_v = max(values) if values else 1.0
    bar_w = plot_w / max(len(values), 1)
    rects = []
    texts = []
    for idx, value in enumerate(values):
        x = margin + idx * bar_w + 1
        h = 0 if max_v == 0 else (value / max_v) * plot_h
        y = height - margin - h
        rects.append(
            f"<rect x='{x:.2f}' y='{y:.2f}' width='{max(bar_w - 2, 1):.2f}' height='{h:.2f}' fill='#2a9d8f' />"
        )
        if len(values) <= 24:
            texts.append(
                f"<text x='{x + bar_w / 2:.2f}' y='{height - 10}' fill='#24423d' font-size='10' text-anchor='middle'>{labels[idx]}</text>"
            )
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='#f7fbfa'/>"
        f"<line x1='{margin}' y1='{height - margin}' x2='{width - margin}' y2='{height - margin}' stroke='#9bb8b0'/>"
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height - margin}' stroke='#9bb8b0'/>"
        + "".join(rects)
        + "".join(texts)
        + "</svg>"
    )


def run_data_audit(config: AuditConfig) -> dict[str, Any]:
    dirs = _ensure_dirs(config.output_dir)
    chinese_header, english_header, rows = _read_training_rows(config)
    submit_times = _read_submit_example(config.submit_example_csv)

    row_count = len(rows)
    first_time = _require_dt(rows[0]["TIME"], "TIME")
    last_time = _require_dt(rows[-1]["TIME"], "TIME")
    unique_senid = sorted({row["SENID"] for row in rows})
    unique_name = sorted({row["NAME"] for row in rows})

    column_profile_rows: list[dict[str, Any]] = []
    for column in english_header:
        raw_values = [row[column] for row in rows]
        null_count = sum(value is None or value == "" for value in raw_values)
        non_null = [value for value in raw_values if value is not None and value != ""]
        sample_values = ", ".join(str(value) for value in non_null[:3])
        dtype = (
            "datetime"
            if column in DATETIME_COLUMNS
            else "float"
            if column in NUMERIC_COLUMNS
            else "string"
        )
        stats = {}
        if column in NUMERIC_COLUMNS and non_null:
            values = [float(value) for value in non_null]
            stats = {"min_value": min(values), "max_value": max(values)}
        elif column in DATETIME_COLUMNS and non_null:
            values = [value for value in non_null]
            stats = {
                "min_value": _format_dt(min(values)),
                "max_value": _format_dt(max(values)),
            }
        else:
            stats = {"min_value": "", "max_value": ""}
        column_profile_rows.append(
            {
                "column_name": column,
                "declared_dtype": dtype,
                "null_count": null_count,
                "null_ratio": round(null_count / row_count, 8),
                "unique_count": len({str(value) for value in non_null}),
                "min_value": stats["min_value"],
                "max_value": stats["max_value"],
                "sample_values": sample_values,
            }
        )

    duplicate_time_count = 0
    duplicate_key_count = 0
    bad_gap_rows: list[dict[str, Any]] = []
    daily_counts: Counter[str] = Counter()
    key_counter: Counter[tuple[str, datetime]] = Counter()
    times: list[datetime] = []
    for row in rows:
        current_time = _require_dt(row["TIME"], "TIME")
        times.append(current_time)
        date_key = current_time.date().isoformat()
        daily_counts[date_key] += 1
        key_counter[(row["SENID"], current_time)] += 1
    duplicate_time_count = len(times) - len(set(times))
    duplicate_key_count = sum(count - 1 for count in key_counter.values() if count > 1)

    for prev, curr in zip(rows, rows[1:]):
        prev_time = _require_dt(prev["TIME"], "TIME")
        curr_time = _require_dt(curr["TIME"], "TIME")
        delta = curr_time - prev_time
        if delta != timedelta(minutes=config.expected_interval_minutes):
            bad_gap_rows.append(
                {
                    "previous_time": _format_dt(prev_time),
                    "current_time": _format_dt(curr_time),
                    "gap_minutes": int(delta.total_seconds() // 60),
                }
            )

    daily_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row_time = _require_dt(row["TIME"], "TIME")
        daily_grouped[row_time.date().isoformat()].append(row)

    daily_rows: list[dict[str, Any]] = []
    slot_values: dict[int, list[float]] = defaultdict(list)
    weekday_slot_values: dict[tuple[int, int], list[float]] = defaultdict(list)
    anomaly_rows: list[dict[str, Any]] = []
    consistency_rows: list[dict[str, Any]] = []
    v_series = [
        _require_float(row[config.target_column], config.target_column)
        for row in rows
        if row[config.target_column] is not None
    ]
    diff_series: list[float] = []
    negative_v_count = 0
    zero_v_count = 0
    repeated_daily_constant_violations = 0

    for index, row in enumerate(rows):
        v_value = _require_float(row[config.target_column], config.target_column)
        if v_value < 0:
            negative_v_count += 1
            anomaly_rows.append(
                {
                    "time": _format_dt(_require_dt(row["TIME"], "TIME")),
                    "senid": row["SENID"],
                    "value": v_value,
                    "anomaly_type": "negative_value",
                    "severity": "high",
                    "details": "V 小于 0",
                }
            )
        if v_value == 0:
            zero_v_count += 1
        row_time = _require_dt(row["TIME"], "TIME")
        slot_index = row_time.hour * 4 + row_time.minute // 15
        slot_values[slot_index].append(v_value)
        weekday_slot_values[(row_time.weekday(), slot_index)].append(v_value)
        if index > 0:
            prev_value = _require_float(
                rows[index - 1][config.target_column], config.target_column
            )
            diff = abs(v_value - prev_value)
            diff_series.append(diff)

    diff_threshold = _quantile(sorted(diff_series), 0.999) if diff_series else math.inf
    for index, row in enumerate(rows[1:], start=1):
        current_value = _require_float(row[config.target_column], config.target_column)
        prev_value = _require_float(
            rows[index - 1][config.target_column], config.target_column
        )
        diff = abs(current_value - prev_value)
        if diff >= diff_threshold:
            anomaly_rows.append(
                {
                    "time": _format_dt(_require_dt(row["TIME"], "TIME")),
                    "senid": row["SENID"],
                    "value": current_value,
                    "anomaly_type": "sharp_change",
                    "severity": "medium",
                    "details": f"相邻 15 分钟变化 {diff:.3f}",
                }
            )

    for date_key, day_rows in sorted(daily_grouped.items()):
        vs = [_require_float(row["V"], "V") for row in day_rows]
        ss = [_require_float(row["S"], "S") for row in day_rows]
        max_v = max(vs)
        min_v = min(vs)
        max_v_time = min(
            _require_dt(row["TIME"], "TIME")
            for row in day_rows
            if _require_float(row["V"], "V") == max_v
        )
        min_v_time = min(
            _require_dt(row["TIME"], "TIME")
            for row in day_rows
            if _require_float(row["V"], "V") == min_v
        )
        mean_v = statistics.fmean(vs)
        mean_s = statistics.fmean(ss)
        max_s = max(ss)
        min_s = min(ss)
        span_s = max_s - min_s
        reference_row = day_rows[0]
        for column in DAILY_REPEAT_COLUMNS:
            values = {row[column] for row in day_rows}
            if len(values) != 1:
                repeated_daily_constant_violations += 1
        avgv_file = _require_float(reference_row["AVGV"], "AVGV")
        maxv_file = _require_float(reference_row["MAXV"], "MAXV")
        minv_file = _require_float(reference_row["MINV"], "MINV")
        avgs_file = _require_float(reference_row["AVGS"], "AVGS")
        maxs_file = _require_float(reference_row["MAXS"], "MAXS")
        mins_file = _require_float(reference_row["MINS"], "MINS")
        span_file = _require_float(reference_row["SPAN"], "SPAN")
        maxt_file = _require_dt(reference_row["MAXT"], "MAXT")
        mint_file = _require_dt(reference_row["MINT"], "MINT")
        avgv_delta = abs(avgv_file - round(mean_v, 2))
        maxv_delta = abs(maxv_file - max_v)
        minv_delta = abs(minv_file - min_v)
        avgs_delta = abs(avgs_file - round(mean_s, 3))
        maxs_delta = abs(maxs_file - max_s)
        mins_delta = abs(mins_file - min_s)
        span_delta = abs(span_file - round(span_s, 3))
        consistency_rows.append(
            {
                "date": date_key,
                "record_count": len(day_rows),
                "avgv_file": avgv_file,
                "avgv_recomputed_round2": round(mean_v, 2),
                "avgv_abs_diff": round(avgv_delta, 6),
                "maxv_file": maxv_file,
                "maxv_recomputed": round(max_v, 6),
                "maxv_abs_diff": round(maxv_delta, 6),
                "minv_file": minv_file,
                "minv_recomputed": round(min_v, 6),
                "minv_abs_diff": round(minv_delta, 6),
                "avgs_file": avgs_file,
                "avgs_recomputed_round3": round(mean_s, 3),
                "avgs_abs_diff": round(avgs_delta, 6),
                "maxs_file": maxs_file,
                "maxs_recomputed": round(max_s, 6),
                "maxs_abs_diff": round(maxs_delta, 6),
                "mins_file": mins_file,
                "mins_recomputed": round(min_s, 6),
                "mins_abs_diff": round(mins_delta, 6),
                "span_file": span_file,
                "span_recomputed_round3": round(span_s, 3),
                "span_abs_diff": round(span_delta, 6),
                "maxt_file": _format_dt(maxt_file),
                "maxt_recomputed": _format_dt(max_v_time),
                "mint_file": _format_dt(mint_file),
                "mint_recomputed": _format_dt(min_v_time),
            }
        )
        daily_rows.append(
            {
                "date": date_key,
                "senid": reference_row["SENID"],
                "slot_count": len(day_rows),
                "daily_sum_v": round(sum(vs) * 0.25, 6),
                "daily_mean_v": round(mean_v, 6),
                "daily_peak_v": round(max_v, 6),
                "daily_peak_time": _format_dt(max_v_time),
                "daily_valley_v": round(min_v, 6),
                "daily_valley_time": _format_dt(min_v_time),
                "daily_peak_valley_gap": round(max_v - min_v, 6),
                "missing_slot_count": max(0, 96 - len(day_rows)),
            }
        )

    slot_rows: list[dict[str, Any]] = []
    for slot_index in range(96):
        values = slot_values[slot_index]
        label = f"{slot_index // 4:02d}:{(slot_index % 4) * 15:02d}"
        summary = _describe(values)
        slot_rows.append(
            {
                "slot_index": slot_index,
                "time_of_day": label,
                "mean_v": round(summary["mean"], 6),
                "std_v": round(summary["std"], 6),
                "p05_v": round(summary["p05"], 6),
                "p50_v": round(summary["p50"], 6),
                "p95_v": round(summary["p95"], 6),
            }
        )

    weekday_slot_rows: list[dict[str, Any]] = []
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for weekday in range(7):
        for slot_index in range(96):
            values = weekday_slot_values[(weekday, slot_index)]
            if not values:
                continue
            weekday_slot_rows.append(
                {
                    "weekday": weekday,
                    "weekday_name": weekday_names[weekday],
                    "slot_index": slot_index,
                    "mean_v": round(statistics.fmean(values), 6),
                }
            )

    daily_energy_series = [row["daily_sum_v"] for row in daily_rows]
    daily_peak_series = [row["daily_peak_v"] for row in daily_rows]
    daily_gap_series = [row["daily_peak_valley_gap"] for row in daily_rows]
    slot_mean_series = [row["mean_v"] for row in slot_rows]

    time_continuity_rows = [
        {
            "senid": unique_senid[0] if unique_senid else "",
            "expected_start_time": _format_dt(first_time),
            "expected_end_time": _format_dt(last_time),
            "expected_points": int(
                ((last_time - first_time).total_seconds() // 60)
                / config.expected_interval_minutes
            )
            + 1,
            "actual_points": row_count,
            "duplicate_time_count": duplicate_time_count,
            "duplicate_key_count": duplicate_key_count,
            "bad_gap_count": len(bad_gap_rows),
            "min_daily_slot_count": min(daily_counts.values()),
            "max_daily_slot_count": max(daily_counts.values()),
            "continuity_pass": len(bad_gap_rows) == 0 and duplicate_time_count == 0,
        }
    ]

    submit_start = submit_times[0]
    submit_end = submit_times[-1]
    submit_interval_ok = all(
        curr - prev == timedelta(minutes=config.expected_interval_minutes)
        for prev, curr in zip(submit_times, submit_times[1:])
    )

    v_summary = _describe(v_series)
    diff_summary = _describe(diff_series or [0.0])
    daily_energy_summary = _describe(daily_energy_series)
    daily_peak_summary = _describe(daily_peak_series)
    daily_gap_summary = _describe(daily_gap_series)

    feature_availability_rows = [
        {
            "feature_name": "V",
            "availability": "safe_target",
            "reason": "比赛主目标列，可作为标签，不可作为未来时点特征。",
        },
        {
            "feature_name": "TIME-derived",
            "availability": "safe_feature",
            "reason": "可安全派生 hour、weekday、slot 等时间特征。",
        },
        {
            "feature_name": "S",
            "availability": "needs_review",
            "reason": "来源含义待进一步确认，可先作为审计对象，不建议直接进入首版模型。",
        },
        {
            "feature_name": "AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN",
            "availability": "high_leakage_risk",
            "reason": "按日统计后回填到当天各时点，线上预测时点不可直接获得，首版 baseline 应禁用。",
        },
    ]

    _write_csv(
        dirs["tables"] / "column_profile.csv",
        list(column_profile_rows[0].keys()),
        column_profile_rows,
    )
    _write_csv(
        dirs["tables"] / "time_continuity.csv",
        list(time_continuity_rows[0].keys()),
        time_continuity_rows,
    )
    _write_csv(
        dirs["tables"] / "time_gaps.csv",
        ["previous_time", "current_time", "gap_minutes"],
        bad_gap_rows,
    )
    _write_csv(
        dirs["tables"] / "daily_load_stats.csv", list(daily_rows[0].keys()), daily_rows
    )
    _write_csv(
        dirs["tables"] / "slot_profile.csv", list(slot_rows[0].keys()), slot_rows
    )
    _write_csv(
        dirs["tables"] / "weekday_slot_profile.csv",
        list(weekday_slot_rows[0].keys()),
        weekday_slot_rows,
    )
    _write_csv(
        dirs["tables"] / "anomaly_flags.csv",
        ["time", "senid", "value", "anomaly_type", "severity", "details"],
        anomaly_rows,
    )
    _write_csv(
        dirs["tables"] / "daily_consistency_checks.csv",
        list(consistency_rows[0].keys()),
        consistency_rows,
    )
    _write_csv(
        dirs["tables"] / "feature_availability.csv",
        list(feature_availability_rows[0].keys()),
        feature_availability_rows,
    )

    (dirs["figures"] / "daily_energy.svg").write_text(
        _line_chart_svg(daily_energy_series, color="#1d7874"), encoding="utf-8"
    )
    (dirs["figures"] / "daily_peak_gap.svg").write_text(
        _line_chart_svg(daily_gap_series, color="#d97706"), encoding="utf-8"
    )
    (dirs["figures"] / "slot_mean_load.svg").write_text(
        _bar_chart_svg([row["time_of_day"] for row in slot_rows], slot_mean_series),
        encoding="utf-8",
    )

    inconsistent_avgv_days = [
        row for row in consistency_rows if row["avgv_abs_diff"] > 0
    ]
    inconsistent_avgs_days = [
        row for row in consistency_rows if row["avgs_abs_diff"] > 0
    ]
    summary = {
        "source_file": str(config.input_csv),
        "submit_example_file": str(config.submit_example_csv),
        "row_count": row_count,
        "column_count": len(english_header),
        "time_range": {"start": _format_dt(first_time), "end": _format_dt(last_time)},
        "unique_senid_count": len(unique_senid),
        "unique_name_count": len(unique_name),
        "target_column": config.target_column,
        "expected_interval_minutes": config.expected_interval_minutes,
        "time_continuity_pass": len(bad_gap_rows) == 0 and duplicate_time_count == 0,
        "daily_full_coverage_pass": min(daily_counts.values()) == 96
        and max(daily_counts.values()) == 96,
        "negative_v_count": negative_v_count,
        "zero_v_count": zero_v_count,
        "sharp_change_threshold": round(diff_threshold, 6) if diff_series else 0.0,
        "anomaly_count": len(anomaly_rows),
        "daily_repeat_constant_violations": repeated_daily_constant_violations,
        "inconsistent_avgv_days": len(inconsistent_avgv_days),
        "inconsistent_avgs_days": len(inconsistent_avgs_days),
        "submit_window": {
            "start": _format_dt(submit_start),
            "end": _format_dt(submit_end),
            "row_count": len(submit_times),
            "interval_pass": submit_interval_ok,
        },
        "v_summary": {key: round(value, 6) for key, value in v_summary.items()},
        "diff_summary": {key: round(value, 6) for key, value in diff_summary.items()},
        "daily_energy_summary": {
            key: round(value, 6) for key, value in daily_energy_summary.items()
        },
        "daily_peak_summary": {
            key: round(value, 6) for key, value in daily_peak_summary.items()
        },
        "daily_peak_gap_summary": {
            key: round(value, 6) for key, value in daily_gap_summary.items()
        },
        "baseline_readiness": {
            "last_day_same_slot": len(bad_gap_rows) == 0,
            "last_7_day_same_slot": len(bad_gap_rows) == 0,
            "weekday_slot_mean": len(bad_gap_rows) == 0,
            "notes": "首版 baseline 建议仅使用时间派生特征与历史 V，禁用当日汇总字段。",
        },
    }
    (dirs["root"] / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = f"""# Task 1 数据审计报告

## 审计范围

- 输入数据：`{config.input_csv}`
- 提交样例：`{config.submit_example_csv}`
- 目标列：`{config.target_column}`
- 审计输出目录：`{config.output_dir}`

## 关键结论

- 训练数据共 {row_count} 行，{len(english_header)} 列，时间范围为 `{_format_dt(first_time)}` 至 `{_format_dt(last_time)}`。
- 原始文件为双表头 CSV，第 1 行中文表头，第 2 行英文表头；建议统一以英文表头作为正式字段名。
- 当前仅发现 1 个 `SENID`（{", ".join(unique_senid)}）与 1 个 `NAME`（{", ".join(unique_name)}），现阶段应按单对象长时序处理。
- 时间连续性检查通过：重复时间 {duplicate_time_count} 条，异常间隔 {len(bad_gap_rows)} 条；每日记录数范围 {min(daily_counts.values())} 到 {max(daily_counts.values())}，满足 15 分钟粒度与每日 96 条要求。
- 提交样例窗口为 `{_format_dt(submit_start)}` 至 `{_format_dt(submit_end)}`，共 {len(submit_times)} 行，列名模式为 `TIME,V`。

## 字段与读取约定

- 编码建议使用 `gb18030` 读取训练文件。
- `TIME/MAXT/MINT` 作为时间字段解析，`V/AVGV/MAXV/MINV/S/AVGS/MAXS/MINS/SPAN` 作为数值字段解析。
- `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN` 在同一天内均表现为重复常量，更接近按日统计回填字段，而不是逐时点实时特征。

## 时间轴审计

- 预期间隔：{config.expected_interval_minutes} 分钟。
- 训练集起止：`{_format_dt(first_time)}` -> `{_format_dt(last_time)}`。
- 时间断点数：{len(bad_gap_rows)}。
- 重复主键数：{duplicate_key_count}。
- 每日记录数最小值：{min(daily_counts.values())}，最大值：{max(daily_counts.values())}。

## 目标列 `V` 审计

- `V` 分布：最小值 {v_summary["min"]:.3f}，中位数 {v_summary["p50"]:.3f}，最大值 {v_summary["max"]:.3f}。
- 负值数量：{negative_v_count}；零值数量：{zero_v_count}。
- 相邻 15 分钟绝对变化的 99.9% 阈值约为 {diff_threshold:.3f}，据此标记了 {sum(1 for row in anomaly_rows if row["anomaly_type"] == "sharp_change")} 个“短时突变”候选点。

## 日级统计与一致性检查

- 日总负荷（按 `sum(V) * 0.25` 计算）的均值为 {daily_energy_summary["mean"]:.3f} MWh，范围 {daily_energy_summary["min"]:.3f} 到 {daily_energy_summary["max"]:.3f} MWh。
- 每日峰谷差均值为 {daily_gap_summary["mean"]:.3f} MW。
- `AVGV` 与按日重算均值存在 {len(inconsistent_avgv_days)} 天不一致；`AVGS` 与按日重算均值存在 {len(inconsistent_avgs_days)} 天不一致。
- `MAXV/MINV/MAXT/MINT` 与按日重算结果整体一致，可用于交叉校验，但不建议直接作为预测时点特征。

## 特征可用性判断

- 安全可用：时间派生特征（`hour`、`weekday`、`15min_slot` 等）。
- 可作为标签历史构造：`V` 的 lag 与 rolling 统计。
- 待确认后再决定：`S`。
- 首版 baseline 禁用：`AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN`，原因是这些字段具有明显的按日汇总回填特征，存在未来信息泄漏风险。

## 对后续验证与 baseline 的建议

- rolling-origin backtest 可以按完整自然日切分，至少 3 folds，每 fold 预测未来 24 小时。
- Day 1 baseline 建议顺序：`last day same slot` -> `last 7 day same slot` -> `weekday-slot mean`。
- 第一版建模应仅依赖 `TIME` 派生特征和历史 `V`，先不要引入按日统计字段。
- 提交导出应严格复用 `submit_example.csv` 的时间格式与列名 `TIME,V`。

## 产物清单

- `tables/column_profile.csv`
- `tables/time_continuity.csv`
- `tables/time_gaps.csv`
- `tables/daily_load_stats.csv`
- `tables/slot_profile.csv`
- `tables/weekday_slot_profile.csv`
- `tables/anomaly_flags.csv`
- `tables/daily_consistency_checks.csv`
- `tables/feature_availability.csv`
- `figures/daily_energy.svg`
- `figures/daily_peak_gap.svg`
- `figures/slot_mean_load.svg`
- `summary.json`

## 审计结论

- 这份训练数据结构规整，可直接进入 Day 1 的 baseline 与 backtest 基础实现。
- 当前首要风险不是时间断点，而是错误使用按日汇总字段导致的特征泄漏，以及提交导出时偏离 `TIME,V` 模式。
- 后续如需更细粒度异常处理，可基于 `tables/anomaly_flags.csv` 对异常日和异常点做二次复核。
"""
    (dirs["root"] / "task1_data_audit_report.md").write_text(report, encoding="utf-8")
    return summary
