__author__ = 'robert'


import sys
import os
if (sys.version_info < (2, 7, 0)):
    import unittest2 as unittest
else:
    import unittest

from pypet import Trajectory
import pypet

class LoadOldTrajectoryTest(unittest.TestCase):

    def test_backwards_compatibility(self):
        if (sys.version_info < (3, 0, 0)):
            # Test only makes sense with python 2.7 or lower
            old_pypet_traj = Trajectory()
            module_path, init_file = os.path.split(pypet.__file__)
            filename= os.path.join(module_path, 'tests','testdata','pypet_v0_1b_6.hdf5')
            old_pypet_traj.f_load(filename=filename,
                                  load_all=2, force=True, index=-1)

            self.assertTrue(old_pypet_traj.v_version=='0.1b.6')
            self.assertTrue(old_pypet_traj.par.x==0)
            self.assertTrue(len(old_pypet_traj)==9)
            self.assertTrue(old_pypet_traj.res.runs.r_4.z==12)
        else:
            pass