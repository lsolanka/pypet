

from pypet.parameter import *
from pypet.trajectory import Trajectory, SingleRun
import numpy as np
import scipy.sparse as spsp
import pypet.utils.explore as ut
from multiprocessing import log_to_stderr, get_logger, Pool, freeze_support, Manager
from multiprocessing.synchronize import Lock
import pickle


def main():
    
    logging.basicConfig(level=logging.DEBUG)
    traj = Trajectory(name='MyTrajectory',filename='../experiments/test.hdf5')
    
    config.multiproc = True
    
    #traj.load_trajectory(trajectoryname='MyTrajectory_2013_05_23_14h29m26s')
    
    traj.f_add_parameter('test.testparam', **{'Fuechse':1,'Sapiens':1,'Comment':'ladida'})

    traj.last.foo = 'bar'
    
    traj.f_add_parameter('Network.Cm')
    
    traj.Parameters.Network.Cm.value= 1.0
    traj.Parameters.Network.Cm.unit = 'pF'
    
    print traj.Parameters.Network.Cm()
    
    
    traj.last.herbert = 4.5
    
    traj.Parameters.test.testparam.Konstantin = 'Konstantin'
    

    traj.f_add_parameter(full_parameter_name='honky', **{'mirta':np.array([[1,2,7],[3,2,17]])})

    traj.f_add_parameter('flonky',**{'val' : 10})
    
    
    param1 = traj.Parameters.test.testparam
    param2 = traj.Parameters.honky
    param3 = traj.last
    
    print param1()
    
    print param3('val')
    
    exp2_list = range(3)
    exp1_list = range(3)
    exp3_list = range(3)
    explore_dict = { param1.gfn('Sapiens') : exp1_list,
                     param2.get_fullname('mirta'):exp2_list,
                     param3.gfn('val') : exp3_list}
    
    cmb_list=[(param3.gfn('val'),param1.gfn('Sapiens'))]
    
    traj.f_add_derived_parameter(full_parameter_name='foo', **{'bar' : -1}).moo = 'zip'
    
    lilma = spsp.lil_matrix((10000,1000))
    lilma[0,100] = 555
    lilma[9999,999] = 11
    traj.f_add_parameter('sparse', mat=lilma, param_type = SparseParameter)
    
    
    traj.f_explore(ut.cartesian_product,explore_dict,cmb_list)
    
    traj._prepare_experiment()
    traj.f_store()

    for n in xrange(len(traj)):
        do_stuff(traj._make_single_run(n))



def do_stuff(srun):
    assert isinstance(srun, SingleRun)
    srun.f_add_parameter(full_parameter_name='foo', **{'bar' : srun._idx})
    srun.store_to_hdf5()
    print srun._idx
    print srun.honky.mirta
    print 'woop'
    print srun.DerivedParameters.pwt.foo.bar
    print srun.pt.DerivedParameters.pwt.foo.bar
    

if __name__ == '__main__':
    main()