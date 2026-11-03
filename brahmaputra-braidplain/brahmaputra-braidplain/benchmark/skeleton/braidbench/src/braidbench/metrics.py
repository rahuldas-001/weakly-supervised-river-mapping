"""Evaluation metrics.

Three families:
  1. Standard segmentation: IoU, Dice, per-class F1
  2. Geometric: channel width, bar width, thread count, bar unit count against
     manually digitised cross-sections
  3. Temporal consistency: fraction of physically implausible year-to-year class
     transitions. This is the metric no published fluvial work reports.
"""
