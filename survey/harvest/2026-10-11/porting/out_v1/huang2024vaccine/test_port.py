# test_port.py
# Left empty on purpose: the verdict for huang2024vaccine is `not_expressible`.
#
# There is no mechanism to test without a model, because the method's mechanism is itself a
# model-training procedure: per-layer embedding gradients, a hook-perturbed second forward
# pass, and a server-side optimizer step. None of these can be assembled from the plugin
# interface, so any assertion written here would be testing a different method.
#
# The reason is recorded in the report (missing_runtime / extraction_needs) and in the class
# docstring of plugin.py.
