# test_port.py
# Left empty on purpose (rule 8, verdict `not_expressible`): the method has no mechanism this library
# can drive, so there is no synthetic situation in which STRIP would act to assert against.
#
# A test here could only re-assert the absence: that Strip.run raises NotImplementedError, or that no
# ModelHandle method returns a class distribution. Neither verifies a mechanism of the method, and the
# softmax forward that every step hangs on (step 3) cannot be supplied by `harness` -- StubHandle only
# counts passes, it does not classify.
