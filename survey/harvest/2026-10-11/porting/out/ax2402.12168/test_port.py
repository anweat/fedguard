# test_port.py
# Empty by design (rule 8): PSIM is not expressible in fedguard, so there is no defense mechanism to
# test. No stage runs outside a training round, no stage or action starts the second PEFT training
# that produces PSIM, no view carries labels or class probabilities, and no action drops an inference
# request. The per-step reasons are in the report.
