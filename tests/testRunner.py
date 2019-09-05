import testSetup
import unittest
import sanityPreCheck 

suite = unittest.TestLoader().loadTestsFromModule(sanityPreCheck)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(result.wasSuccessful())
