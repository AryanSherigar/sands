"""Authored conditions, grouped by a one-letter label prefix.

Conditions apply in label order (G, B, A, R, T, P, M, W), and a later condition
sees the mutations of an earlier one within the same turn. The narrator never
changes House or retainer numbers: it sets an `intent.*` flag and the matching
condition applies the effect on the next turn.
"""
