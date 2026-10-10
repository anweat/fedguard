# test_port.py
# Intentionally empty (rule 8): the verdict for xie2024gradsafe is `not_expressible`, so there is no
# mechanism to drive. The detection needs the gradient of the aligned base LLM's loss on a constructed
# (prompt, `Sure`) pair with respect to the frozen base weights, and no fedguard interface produces it.
# A test here could only assert that an empty shell returns an empty shell's finding, which is not a test
# of the method.
#
# The mechanism worth testing once that runtime exists: build a small synthetic batch of prompts whose
# per-slice cosine vectors are known, make one align with the stored unsafe reference above the
# detection threshold and another sit near zero, then assert that the first is masked out through
# `mask_samples` at CLIENT_PRE_TRAIN (DataView.manifest hashes, ClientGuard.kept_indices()) and that
# the second survives.
