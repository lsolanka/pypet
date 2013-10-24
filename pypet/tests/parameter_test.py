

__author__ = 'Robert Meyer'


import numpy as np

import sys
if (sys.version_info < (2, 7, 0)):
    import unittest2 as unittest
else:
    import unittest

from pypet.parameter import Parameter, PickleParameter, BaseParameter, ArrayParameter, SparseParameter
import pickle
import scipy.sparse as spsp
import pypet.pypetexceptions as pex
from pypet.utils.helpful_functions import nested_equal
import warnings


class ParameterTest(unittest.TestCase):


    def test_deprecated_methods_that_have_new_names(self):
        for param in self.param.values():
            with warnings.catch_warnings(record=True) as warnings_list:
                # Cause all warnings to always be triggered.
                warnings.simplefilter("always")
                # Trigger a warning.
                self.assertEqual(param.v_parameter, param.v_is_parameter)
                self.assertEqual(param.v_leaf, param.v_is_leaf)
                self.assertEqual(param.f_is_root(), param.v_is_root)
                self.assertEqual(param.v_fast_accessible, param.f_supports_fast_access())
                # Verify some things
                assert len(warnings_list) == 4
                for warning in warnings_list:
                    assert issubclass(warning.category, DeprecationWarning)
                    assert "deprecated" in str(warning.message)


    def test_deprecated_range_methods_that_have_new_names(self):
        for param in self.param.values():
            with warnings.catch_warnings(record=True) as warnings_list:
                # Cause all warnings to always be triggered.
                warnings.simplefilter("always")
                # Trigger a warning.
                self.assertEqual(param.f_is_array(), param.f_has_range())
                if param.f_has_range():
                    self.assertEqual(id(param.f_get_array()),id(param.f_get_range()))
                # Verify some things
                assert len(warnings_list) == 1 or len(warnings_list)==2
                for warning in warnings_list:
                    assert issubclass(warning.category, DeprecationWarning)
                    assert "deprecated" in str(warning.message)



    def testMetaSettings(self):
        for key, param in self.param.items():
            self.assertEqual(param.v_full_name, self.location+'.'+key)
            self.assertEqual(param.v_name, key)
            self.assertEqual(param.v_location, self.location)


    def make_params(self):
        self.param = {}
        for key, val in self.data.items():
            self.param[key] = Parameter(self.location+'.'+key, val, comment=key)


    def setUp(self):

        if not hasattr(self,'data'):
            self.data={}

        self.data['val0']= 1
        self.data['val1']= 1.0
        self.data['val2']= True
        self.data['val3'] = 'String'
        self.data['npfloat'] = np.array([1.0,2.0,3.0])
        self.data['npfloat_2d'] = np.array([[1.0,2.0],[3.0,4.0]])
        self.data['npbool']= np.array([True,False, True])
        self.data['npstr'] = np.array(['Uno', 'Dos', 'Tres'])
        self.data['npint'] = np.array([1,2,3])

        self.location = 'MyName.Is.myParam'


        self.make_params()


        # with self.assertRaises(AttributeError):
        #     self.param.val0.f_set([[1,2,3],[1,2,3]])

        #Add explortation:
        self.explore()

    def test_get_item(self):
        for paramname in self.explore_dict:
            param = self.param[paramname]
            val1=param.f_get_range()[1]
            val2=param[1]
            self.assertTrue(nested_equal(val1,val2), '%s != %s' % (str(val1),str(val2)))

    def test_type_error_for_get_item(self):
        for name,param in self.param.items():
            if not name in self.explore_dict:
                with self.assertRaises(TypeError):
                    param[1]

    def test_type_error_for_shrink(self):
        for name,param in self.param.items():
            if not name in self.explore_dict:
                with self.assertRaises(TypeError):
                    param._shrink()

    def explore(self):
        self.explore_dict={'npstr':[np.array(['Uno', 'Dos', 'Tres']),
                               np.array(['Cinco', 'Seis', 'Siette']),
                            np.array(['Ocho', 'Nueve', 'Diez'])],
                           'val0':[1,2,3]}

        ## Explore the parameter:
        for key, vallist in self.explore_dict.items():
            self.param[key]._explore(vallist)




    def test_the_insertion_made_implicetly_in_setUp(self):
        for key, val in self.data.items():

            if not key in self.explore_dict:
                self.param[key]._restore_default()
                param_val = self.param[key].f_get()
                self.assertTrue(np.all(str(val) == str(param_val)),'%s != %s'  %(str(val),str(param_val)))



    def test_expanding_type_error(self):
        for name,param in self.param.items():
            if not name in self.explore_dict:
                #Test locking
                with self.assertRaises(TypeError):
                    param._expand([1,2,3])

                #Test wron param type
                with self.assertRaises(TypeError):
                    param.f_unlock()
                    param._expand([1,2,3])


    def test_rename(self):
        for name,param in self.param.iteritems():
            param._rename('test.test.wirsing')
            self.assertTrue(param.v_name=='wirsing')
            self.assertTrue(param.v_full_name=='test.test.wirsing')
            self.assertTrue(param.v_location=='test.test')



    def test_expanding(self):
        for name,param in self.param.items():
            if name in self.explore_dict:
                param.f_unlock()
                param._expand(self.explore_dict[name])

                self.assertTrue(len(param) == 2*len(self.explore_dict[name]),
                                'Expanding of %s did not work.' % name)


    def test_exploration(self):
        for key, vallist in self.explore_dict.items():

            param = self.param[key]

            for idx, val in enumerate(vallist):
                assert isinstance(param, BaseParameter)
                param._set_parameter_access(idx)

                self.assertTrue(np.all(repr(param.f_get())==repr(val))),'%s != %s'%( str(param.f_get()),str(val))

                param_val = self.param[key].f_get_range()[idx]
                self.assertTrue(np.all(str(val) == str(param_val)),'%s != %s'  %(str(val),str(param_val)))

            param._restore_default()
            val = self.data[key]
            self.assertTrue(np.all(repr(param.f_get())==repr(val))),'%s != %s'%( str(param.f_get()),str(val))


    def test_storage_and_loading(self):

        for key, param in self.param.items():
            store_dict = param._store()

            constructor = param.__class__

            param.f_unlock()
            param.f_empty()

            param = constructor('')

            param._load(store_dict)

            param._rename(self.location+'.'+key)

            self.param[key] = param


        self.test_the_insertion_made_implicetly_in_setUp()

        self.test_exploration()

        self.testMetaSettings()


    def test_pickling_without_multiprocessing(self):
        for key, param in self.param.items():
            param.f_unlock()
            param.v_full_copy=True

            dump = pickle.dumps(param)

            newParam = pickle.loads(dump)



            self.param[key] = newParam

        self.test_exploration()

        self.test_the_insertion_made_implicetly_in_setUp()

        self.testMetaSettings()


    def test_pickling_with_multiprocessing(self):
        for key, param in self.param.items():
            param.f_unlock()
            param.v_full_copy=False

            dump = pickle.dumps(param)

            newParam = pickle.loads(dump)



            self.param[key] = newParam

        #self.test_exploration()

        self.test_the_insertion_made_implicetly_in_setUp()

        self.testMetaSettings()

    def test_resizing_and_deletion(self):

        for key, param in self.param.items():
            param.f_lock()
            with self.assertRaises(pex.ParameterLockedException):
                 param.f_set(42)

            with self.assertRaises(pex.ParameterLockedException):
                param._shrink()


            param.f_unlock()


            if len(param)> 1:
                self.assertTrue(param.f_has_range())

            if param.f_has_range():
                self.assertTrue(len(param)>1)
                param._shrink()

            self.assertTrue(len(param) == 1)

            self.assertFalse(param.f_is_empty())
            self.assertFalse(param.f_has_range())



            param.f_empty()

            self.assertTrue(param.f_is_empty())
            self.assertFalse(param.f_has_range())

class ArrayParameterTest(ParameterTest):

    def setUp(self):


        if not hasattr(self,'data'):
            self.data= {}


        self.data['myinttuple'] = (1,2,3)
        self.data['mydoubletuple'] = (42.0,43.7,33.3)
        self.data['mystringtuple'] = ('Eins','zwei','dr3i')

        super(ArrayParameterTest,self).setUp()

        ## For the rest of the checkings, lists are converted to tuples:
        for key, val in self.data.items():
            if isinstance(val, list):
                self.data[key] = tuple(val)


    def make_params(self):
        self.param = {}
        for key, val in self.data.items():
            self.param[key] = ArrayParameter(self.location+'.'+key, val, comment=key)


    def explore(self):

        matrices = []


        self.explore_dict={'npstr':[np.array(['Uno', 'Dos', 'Tres']),
                               np.array(['Cinco', 'Seis', 'Siette']),
                            np.array(['Ocho', 'Nueve', 'Diez'])],
                           'val0':[1,2,3],
                           'myinttuple':[(1,2,1),(4,5,6),(5,6,7)]}

        ### Convert the explored stuff into numpy arrays
        #for idx, val in enumerate(self.explore_dict['myinttuple']):
         #   self.explore_dict['myinttuple'][idx] = np.array(val)


        ## Explore the parameter:
        for key, vallist in self.explore_dict.items():
            self.param[key]._explore(vallist)


class PickleParameterTest(ParameterTest):

    def setUp(self):


        if not hasattr(self,'data'):
            self.data={}

        self.data['spsparse_csc'] = spsp.csc_matrix((1000,100))
        self.data['spsparse_csc'][1,2] = 44.5

        self.data['spsparse_csr'] = spsp.csr_matrix((2222,22))
        self.data['spsparse_csr'][1,3] = 44.5

        self.data['spsparse_lil'] = spsp.lil_matrix((111,111))
        self.data['spsparse_lil'][3,2] = 44.5

        super(PickleParameterTest,self).setUp()


    def make_params(self):
        self.param = {}
        for key, val in self.data.items():
            self.param[key] = PickleParameter(self.location+'.'+key, val, comment=key)



    def explore(self):

        matrices = []
        for irun in range(3):

            spsparse_lil = spsp.lil_matrix((111,111))
            spsparse_lil[3,2] = 44.5*irun

            matrices.append(spsparse_lil)


        self.explore_dict={'npstr':[np.array(['Uno', 'Dos', 'Tres']),
                               np.array(['Cinco', 'Seis', 'Siette']),
                            np.array(['Ocho', 'Nueve', 'Diez'])],
                           'val0':[1,2,3],
                           'spsparse_lil' : matrices}




        ## Explore the parameter:
        for key, vallist in self.explore_dict.items():
            self.param[key]._explore(vallist)


class SparseParameterTest(ParameterTest):
    def setUp(self):


        if not hasattr(self,'data'):
            self.data={}

        self.data['spsparse_csc'] = spsp.csc_matrix((1000,100))
        self.data['spsparse_csc'][1,2] = 44.5

        self.data['spsparse_csr'] = spsp.csr_matrix((2222,22))
        self.data['spsparse_csr'][1,3] = 44.5

        self.data['spsparse_bsr'] = spsp.csr_matrix((111,111))
        self.data['spsparse_bsr'][3,2] = 44.5
        self.data['spsparse_bsr'] = self.data['spsparse_bsr'].tobsr()

        self.data['spsparse_dia'] = spsp.csr_matrix((111,111))
        self.data['spsparse_dia'][3,2] = 44.5
        self.data['spsparse_dia'] = self.data['spsparse_dia'].todia()

        super(SparseParameterTest,self).setUp()


    def make_params(self):
        self.param = {}
        for key, val in self.data.items():
            self.param[key] = SparseParameter(self.location+'.'+key, val, comment=key)



    def explore(self):

        matrices_csr = []
        for irun in range(3):

            spsparse_csr = spsp.csr_matrix((111,111))
            spsparse_csr[3,2+irun] = 44.5*irun

            matrices_csr.append(spsparse_csr)

        matrices_csc = []
        for irun in range(3):

            spsparse_csc = spsp.csc_matrix((111,111))
            spsparse_csc[3,2+irun] = 44.5*irun

            matrices_csc.append(spsparse_csc)

        matrices_bsr = []
        for irun in range(3):

            spsparse_bsr = spsp.csr_matrix((111,111))
            spsparse_bsr[3,2+irun] = 44.5*irun

            matrices_bsr.append(spsparse_bsr.tobsr())

        matrices_dia = []
        for irun in range(3):

            spsparse_dia = spsp.csr_matrix((111,111))
            spsparse_dia[3,2+irun] = 44.5*irun

            matrices_dia.append(spsparse_dia.todia())


        self.explore_dict={'npstr':[np.array(['Uno', 'Dos', 'Tres']),
                               np.array(['Cinco', 'Seis', 'Siette']),
                            np.array(['Ocho', 'Nueve', 'Diez'])],
                           'val0':[1,2,3],
                           'spsparse_csr' : matrices_csr,
                           'spsparse_csc' : matrices_csc,
                           'spsparse_bsr' : matrices_bsr,
                           'spsparse_dia' : matrices_dia}




        ## Explore the parameter:
        for key, vallist in self.explore_dict.items():
            self.param[key]._explore(vallist)


if __name__ == '__main__':
    unittest.main()
