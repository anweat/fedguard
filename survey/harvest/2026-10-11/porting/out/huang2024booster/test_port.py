# test_port.py
# Empty on purpose (rule 8): there is no plugin object to exercise.
#
# Booster (Huang et al., 2024) is a one-time, centralised alignment-stage training run that produces
# the service's base checkpoint. It is not a per-round transformation of federated data, so no
# synthetic situation can be built in `harness` in which it should act, and none in which it should
# stay still. See plugin.py and the report: verdict `not_expressible`.
