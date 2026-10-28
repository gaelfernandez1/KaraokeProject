"""Baseline steps: today's equivalents of the v2 pipeline, used as the reference to beat.

Heavy libraries (torch, transformers, faster_whisper, demucs) are imported inside methods, so
the runner can import these classes cheaply to read their `version`.
"""
