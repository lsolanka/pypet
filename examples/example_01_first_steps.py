__author__ = 'Robert Meyer'


from pypet import Environment
from pypet.utils.explore import cartesian_product

def multiply(traj):
    """Example of a sophisticated simulation that involves multiplying two values.

    :param traj:

        Trajectory - or more precisely a SingleRun - containing
        the parameters in a particular combination,
        it also serves as a container for results.

    """
    z=traj.x*traj.y
    traj.f_add_result('z', z, comment='Result of our simulation!')



# Create an environment that handles running
env = Environment(trajectory='Multiplication',
                  filename='experiments/example_01/HDF5/example_01.hdf5',
                  file_title='Example_01_First_Steps',
                  log_folder='experiments/example_01/LOGS/',
                  comment='The first example!')

# The environment has created a trajectory container for us
traj = env.v_trajectory

# Add both parameters
traj.f_add_parameter('x', 1, comment='I am the first dimension!')
traj.f_add_parameter('y', 1, comment='I am the second dimension!')

# Explore the parameters with a cartesian product
traj.f_explore(cartesian_product({'x':[1,2,3,4], 'y':[6,7,8]}))

# Run the simulation
env.f_run(multiply)



# Now let's see how we can reload the stored data from above.
# We do not need an environment for that, just a trajectory.
from pypet.trajectory import Trajectory

# So, first let's create a new trajectory and pass it the path and name of the HDF5 file.
# Yet, to be very clear let's delete all the old stuff.
del traj
del env
traj = Trajectory(filename='experiments/example_01/HDF5/example_01.hdf5')

# Now we want to load all stored data.
traj.f_load(index=-1, load_parameters=2, load_results=2)

# Above `index` specifies that we want to load the trajectory with that particular index
# within the HDF5 file. We could instead also specify a `name`.
# Counting works also backwards, so `-1` yields the last or newest trajectory in the file.
#
# Next we need to specify how the data is loaded.
# Therefore, we have to set the keyword arguments `load_parameters` and `load_results`,
# here we chose both to be `2`.
# `0` would mean we do not want to load anything at all.
# `1` would mean we only want to load the empty hulls or skeletons of our parameters
# or results. Accordingly, we would add parameters or results to our trajectory
# but they would not contain any data.
# Instead `2` means we want to load the parameters and results including the data they contain.

# Finally we want to print a result of a particular run.
# Let's take the second run named `run_00000001` (Note that counting starts at 0!).
print 'The result of `run_00000001` is: '
print traj.run_00000001.z