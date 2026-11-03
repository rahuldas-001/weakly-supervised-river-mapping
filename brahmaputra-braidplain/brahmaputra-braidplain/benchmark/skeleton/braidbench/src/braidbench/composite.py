"""Temporally joined Sentinel-1 / Sentinel-2 composite builder.

Move `mask_s2_clouds()` and `build_s1s2_composite_joined()` here.
The saveBest join within `sensors.join_window_days` is the reason SAR bands are
never blank; that behaviour is a documented design decision, not an accident.
"""
