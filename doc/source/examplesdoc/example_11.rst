
.. _example-11:

=================================
11 Large scale BRIAN simulation
=================================

This example involves a large scale simulation of a BRIAN_ network :ref:`brian-framework`.
The example is taken from the `Litwin-Kumar and Doiron paper`_ from Nature neuroscience 2012.


It is split into three different modules: The `clusternet.py` file containing
the network specification, the `runscript.py` file to start a simulation
(you have to be patient, BRIAN simulations can take some time), and
the `plotff.py` to plot the results of the parameter exploration, i.e. the
Fano Factor as a function of the clustering parameter `R_ee`.

Download: :download:`clusternet.py <../../../examples/example_11_large_scale_brian_simulation/clusternet.py>`

Download: :download:`runscript.py <../../../examples/example_11_large_scale_brian_simulation/runscript.py>`

Download: :download:`plotff.py <../../../examples/example_11_large_scale_brian_simulation/plotff.py>`


-------------------
Clusternet
-------------------

.. literalinclude:: ../../../examples/example_11_large_scale_brian_simulation/clusternet.py

----------
Runscript
----------

.. literalinclude:: ../../../examples/example_11_large_scale_brian_simulation/runscript.py

-------
Plotff
-------

.. literalinclude:: ../../../examples/example_11_large_scale_brian_simulation/plotff.py

.. _`Litwin-Kumar and Doiron paper`: http://www.nature.com/neuro/journal/v15/n11/full/nn.3220.html

.. _BRIAN: http://briansimulator.org/