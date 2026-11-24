# Dangerous scenarios to check

| # | Scenario | Voltage (V) | Current (I) | Power (P) | Check / Indicator |
|---|----------|-------------|-------------|-----------|-------------------|
| 1 | Sensor fault / data inconsistency | Any | Any | Any | Implied cos φ = P / (√3·V·I) > 1 or far from the expected 0.9–1 |
| 2 | Short circuit | Very low | Very high | Low or erratic | V collapses while I exceeds rated current |
| 3 | Trip / grid disconnection | Normal or erratic | ≈ 0 | ≈ 0 | No output although wind is available |
| 4 | Poor power factor / converter issue | Normal | Normal | Much lower than V·I implies | Low cos φ, large reactive component |
| 5 | Grid overvoltage | High (> +10% nominal) | Normal or low | Normal | V outside the allowed band |
| 6 | Grid undervoltage | Low (< -10% nominal) | High | Normal or reduced | Current rises to compensate for the voltage drop |
| 7 | Overload / out-of-limits operation | Any | > rated | > rated | Values exceed nameplate limits |
| 8 | Underperformance (icing, erosion, pitch/yaw error) | Normal | Normal | Below the power curve for the given wind | Needs wind speed or comparable reference snapshots |
| 9 | Curtailment | Normal | Normal | Plateau below rated | Same P across snapshots at different wind conditions |
| 10 | Slow degradation (winding / mechanical wear) | Normal | Rising for the same P | Falling for the same wind | Compare snapshots taken on different dates under similar conditions |
| 11 | Phase imbalance (only if values are per phase) | Unequal between phases | Unequal between phases | Reduced | Deviation between phases above a few percent |

