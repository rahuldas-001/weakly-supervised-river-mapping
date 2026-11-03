"""Spatial block splitting.

Replaces the random `create_splits()` in the original notebook. Random tile
assignment with overlapping tiles leaks ground truth between train and test.
See docs/splits.md.
"""
