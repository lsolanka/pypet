from numpy.oldnumeric.ma import _ptp

__author__ = 'robert'


import logging
import tables as pt
import os
import numpy as np
from functools import wraps
from mypet.trajectory import Trajectory,SingleRun
from mypet.parameter import BaseParameter, BaseResult, SimpleResult
from mypet import globally


from mypet.parameter import ObjectTable
from pandas import DataFrame, read_hdf



class MultiprocWrapper(object):


    def store(self,*args,**kwargs):
        raise NotImplementedError('Implement this!')


class QueueStorageServiceSender(MultiprocWrapper):

    def __init__(self):
        self._queue = None

    def set_queue(self,queue):
        self._queue = queue

    def __getstate__(self):
        result = self.__dict__.copy()
        result['_queue'] = None
        return result

    def store(self,*args,**kwargs):
        self._queue.put(('STORE',args,kwargs))


    def send_done(self):
        self._queue.put(('DONE',[],{}))

class QueueStorageServiceWriter(object):
    def __init__(self, storage_service, queue):
        self._storage_service = storage_service
        self._queue = queue

    def run(self):
        while True:
            msg,args,kwargs = self._queue.get()

            if msg == 'DONE':
                break
            elif msg == 'STORE':
                self._storage_service.store(*args,**kwargs)
            else:
                pass
                #raise RuntimeError('You queued something that was not intended to be queued!')

            self._queue.task_done()

class LockWrapper(MultiprocWrapper):
    def __init__(self,storage_service, lock):
        self._storage_service = storage_service
        self._lock = lock


    def store(self,*args,**kwargs):
        try:
            self._lock.acquire()
            self._storage_service.store(*args,**kwargs)
        except Exception, e:
            raise
        finally:
            if not self._lock == None:
                self._lock.release()



class StorageService(object):

    def store(self,stuff_to_store,trajectoryname,*args,**kwargs):
        raise NotImplementedError('Implement this!')

    def load(self,stuff_to_load,trajectoryname,*args,**kwargs):
        raise NotImplementedError('Implement this!')

class LazyStorageService(StorageService):

    def load(self,*args,**kwargs):
        pass

    def store(self,*args,**kwargs):
        pass

    def merge(self,traj1,traj2,*args,**kwargs):
        pass

class HDF5StorageService(StorageService):
    ''' General Service to handle the storage of a Trajectory and Parameters
    '''

    APPEND_PARTS = 'parts'
    APPEND_FULL = 'full'

    def __init__(self, filename=None, filetitle='Experiment'):
        self._filename = filename
        self._filetitle = filetitle
        self._trajectoryname = None
        self._hdf5file = None
        self._trajectorygroup = None
        self._logger = logging.getLogger('mypet.storageservice_HDF5StorageService')
        self._lock = None



    def load(self,stuff_to_load,*args,**kwargs):
        try:

            self._extract_file_information(kwargs)


            args = list(args)

            opened = self._opening_routine('r')


            if isinstance(stuff_to_load,Trajectory):
                self._load_trajectory(stuff_to_load,*args,**kwargs)


            elif isinstance(stuff_to_load, (BaseParameter,BaseResult)):
                self._load_parameter_or_result(stuff_to_load,*args,**kwargs)

            elif isinstance(stuff_to_load, list):
                self._load_several_items(stuff_to_load,*args,**kwargs)

            else:
                raise ValueError('Your loading of >>%s<< (args[0]) did not work, type of >>%s<< not supported' % (str(
                    stuff_to_load),str(type(stuff_to_load))))

            self._closing_routine(opened)
        except Exception,e:
            self._closing_routine(True)
            self._logger.error('Failed loading  >>%s<<' % str(stuff_to_load))
            raise




    def store(self,stuff_to_store,*args,**kwargs):
        try:

            self._extract_file_information(kwargs)


            args = list(args)

            if isinstance(stuff_to_store,Trajectory):
                mode = 'na'
            else:
                mode = 'a'


            opened= self._opening_routine(mode)

            if isinstance(stuff_to_store,Trajectory):

                self._store_trajectory(stuff_to_store,*args,**kwargs)

            elif isinstance(stuff_to_store,SingleRun):

                self._store_single_run(stuff_to_store,*args,**kwargs)

            elif isinstance(stuff_to_store,(BaseParameter,BaseResult)):
                self._store_parameter_or_result(stuff_to_store,*args,**kwargs)

            elif isinstance(stuff_to_store, list):
                self._store_several_items(stuff_to_store,*args,**kwargs)

            else:
                raise ValueError('Your storage of >>%s<< (args[0]) did not work, type of >>%s<< not supported' % (str(
                    stuff_to_store),str(type(stuff_to_store))))

            self._closing_routine(opened)

        except Exception,e:
            self._closing_routine(True)
            self._logger.error('Failed storing >>%s<<' % str(stuff_to_store))
            raise



    def _load_several_items(self,items_list,*args,**kwargs):
        for item in items_list:
            self.load(item,*args,**kwargs)

    def _store_several_items(self,items_list,*args,**kwargs):
        for item in items_list:
            self.store(item,*args,**kwargs)

    def _opening_routine(self,mode):
        if self._hdf5file == None:
                if 'a' in mode or 'w' in mode:
                    (path, filename)=os.path.split(self._filename)
                    if not os.path.exists(path):
                        os.makedirs(path)

                    if 'a' in mode:
                        openmode = 'a'
                    elif 'w' in mode:
                        openmode='w'
                    else:
                        raise RuntimeError('You shall not pass!')

                    self._hdf5file = pt.openFile(filename=self._filename, mode=openmode, title=self._filetitle)
                    if 'n' in mode:
                        self._hdf5file.createGroup(where='/', name= self._trajectoryname, title=self._trajectoryname)

                    if not ('/'+self._trajectoryname) in self._hdf5file:
                        raise ValueError('File %s does not contain trajectory %s.' % (self._filename,
                                                                                      self._trajectoryname))
                    self._trajectorygroup = self._hdf5file.getNode('/'+self._trajectoryname)

                elif mode == 'r':
                    ### Fuck Pandas, we have to wait until the next relaese until this is supported:
                    mode = 'a'
                    if not os.path.isfile(self._filename):
                        raise ValueError('Filename ' + self._filename + ' does not exist.')

                    self._hdf5file = pt.openFile(filename=self._filename, mode=mode, title=self._filetitle)

                    if isinstance(self._trajectoryname,int):
                        nodelist = self._hdf5file.listNodes(where='/')

                        if self._trajectoryname >= len(nodelist) or self._trajectoryname < -len(nodelist):
                            raise ValueError('Trajectory No. %d does not exists, there are only %d trajectories in %s.'
                            % (self._trajectoryname,len(nodelist),self._filename))

                        self._trajectorygroup = nodelist[self._trajectoryname]
                        self._trajectoryname = self._trajectorygroup._v_name
                    else:
                        if not ('/'+self._trajectoryname) in self._hdf5file:
                            raise ValueError('File %s does not contain trajectory %s.' % (self._filename,
                                                                                          self._trajectoryname))
                        self._trajectorygroup = self._hdf5file.getNode('/'+self._trajectoryname)

                else:
                    raise RuntimeError('You shall not pass!')


                return True
        else:
            return False

    def _closing_routine(self, closing):
        if closing and self._hdf5file != None and self._hdf5file.isopen:
            self._hdf5file.flush()
            self._hdf5file.close()
            self._hdf5file = None
            self._trajectorygroup = None
            self._trajectoryname = None
            return True
        else:
            return False

    def _extract_file_information(self,kwargs):
        if 'filename' in kwargs:
            self._filename=kwargs.pop('filename')

        if 'filetitle' in kwargs:
            self._filetitle = kwargs.pop('filetitle')

        if 'trajectoryname' in kwargs:
            self._trajectoryname = kwargs.pop('trajectoryname')





    def __getstate__(self):
        result = self.__dict__.copy()
        del result['_logger']
        result['_lock'] = None
        return result

    def __setstate__(self, statedict):
        self.__dict__.update(statedict)
        self._logger = logging.getLogger('mypet.storageservice_HDF5StorageService=' + self._filename)


    ######################## LOADING A TRAJECTORY #################################################

    def _load_trajectory(self,traj, replace,
                         load_params, load_derived_params, load_results):

        ''' Loads a single trajectory from a given file.

        Per default derived parameters and results are not loaded. If the filename is not specified
        the file where the current trajectory is supposed to be stored is taken.

        If the user wants to load results, the actual data is not loaded, only dummy objects
        are created, which must load their data independently. It is assumed that
        results of many simulations are large and should not be loaded all together into memory.

        If replace is true than the current trajectory name is replaced by the name of the loaded
        trajectory, so is the filename.
        '''

        if replace:
            assert traj.is_empty()
        else:
            traj._loadedfrom= self._filename+': '+self._trajectoryname

        self._load_meta_data(traj, replace)

        self._load_config(traj, load_params)
        self._load_params(traj, load_params)
        self._load_derived_params(traj, load_derived_params)
        self._load_results(traj, load_results)



    def _load_meta_data(self,traj,  replace):
        metatable = self._trajectorygroup.info
        metarow = metatable[0]

        traj._length = metarow['length']

        if replace:
            traj._comment = metarow['comment']
            traj._time = metarow['timestamp']
            traj._formatted_time = metarow['time']
            traj._loadedfrom=(metarow['loaded_from'])



    def _load_config(self,traj,load_params):
        paramtable = self._trajectorygroup.config_table
        self._load_any_param_or_result_table(traj,traj._config,paramtable, load_params)

    def _load_params(self,traj, load_params):
        paramtable = self._trajectorygroup.parameter_table
        self._load_any_param_or_result_table(traj,traj._parameters,paramtable, load_params)

    def _load_derived_params(self,traj, load_derived_params):
        paramtable = self._trajectorygroup.derived_parameter_table
        self._load_any_param_or_result_table(traj,traj._derivedparameters,paramtable, load_derived_params)

    def _load_results(self,traj, load_results):
        resulttable = self._trajectorygroup.result_table
        self._load_any_param_or_result_table(traj,traj._results, resulttable, load_results)


    def _load_any_param_or_result_table(self,traj, wheredict, paramtable, load_mode):
        ''' Loads a single parameter from a pytable.

        :param paramtable: The overiew pytable containing all parameters
        '''
        assert isinstance(paramtable,pt.Table)

        # if len(wheredict) != 0:
        #     raise ValueError('You cannot load instances from %s into your trajectory since your trajectory is not empty.'
        #     % paramtable._v_name)

        if (load_mode == globally.LOAD_SKELETON or
        load_mode == globally.LOAD_DATA or
        load_mode == globally.UPDATE_SKELETON):
            colnames = paramtable.colnames

            for row in paramtable.iterrows():
                location = row['location']
                name = row['name']
                fullname = location+'.'+name
                class_name = row['class_name']


                comment = row['comment']


                if fullname in wheredict:
                    if load_mode == globally.UPDATE_SKELETON:
                        continue
                    else:
                        self._logger.warn('Paremeter or Result >>%s<< is already in your trajectory, I am overwriting it.'
                                                                                 % fullname)

                new_class = traj._create_class(class_name)
                paraminstance = new_class(fullname,comment=comment)
                assert isinstance(paraminstance, (BaseParameter,BaseResult))


                if 'size' in colnames:
                    size = row['size']
                    if size > 1 and size != len(traj):
                        raise RuntimeError('Your are loading a parameter >>%s<< with length %d, yet your trajectory has lenght %d, something is wrong!'
                                           % (fullname,size,len(traj)))
                    elif size > 1:
                        traj._exploredparameters[fullname]=paraminstance
                    elif size == 1:
                        pass
                    else:
                        RuntimeError('You shall not pass!')

                if paramtable._v_name in ['derived_parameter_table', 'result_table']:
                    #creator_name = row['creator_name']
                    creator_id = row['creator_id']
                    if paramtable._v_name == 'derived_parameter_table':
                        if not creator_id in traj._id_to_dpar:
                            traj._id_to_dpar[creator_id] = []
                        traj._id_to_dpar[creator_id].append(paraminstance)
                        traj._dpar_to_id[fullname] = creator_id
                    elif paramtable._v_name == 'result_table':
                        if not creator_id in traj._id_to_res:
                            traj._id_to_res[creator_id] = []
                        traj._id_to_res[creator_id].append(paraminstance)
                        traj._res_to_id[fullname] = creator_id
                    else:
                        raise RuntimeError('You shall not pass!')



                if load_mode == globally.LOAD_DATA:
                    self.load(paraminstance)


                wheredict[fullname]=paraminstance

                traj._nninterface._add_to_nninterface(fullname, paraminstance)


    ######################## Storing a Signle Run ##########################################

    def _store_single_run(self,single_run):
        ''' Stores the derived parameters and results of a single run.
        '''

        assert isinstance(single_run,SingleRun)

        traj = single_run._single_run
        n = single_run.get_n()

        self._logger.info('Start storing run %d with name %s.' % (n,single_run.get_name()))



        paramtable = getattr(self._trajectorygroup, 'derived_parameter_table')
        self._store_single_table(traj._derivedparameters, paramtable, traj.get_name(),n)
        self._store_dict(traj._derivedparameters)


        paramtable = getattr(self._trajectorygroup, 'result_table')
        self._store_single_table(traj._results, paramtable, traj.get_name(),n)
        self._store_dict(traj._results)

        # For better readability add the explored parameters to the results
        self._add_explored_params(single_run)

        self._logger.info('Finished storing run %d with name %s' % (n,single_run.get_name()))



    def _add_explored_params(self, single_run):
        ''' Stores the explored parameters as a Node in the HDF5File under the results nodes for easier comprehension of the hdf5file.
        '''
        paramdescriptiondict={'location': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                'name': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                'class_name': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                'value' :pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH)}

        where = 'results.'+single_run.get_name()
        rungroup = self._create_groups(where)

        paramtable = self._hdf5file.createTable(where=rungroup, name='explored_parameter_table',
                                                description=paramdescriptiondict, title='explored_parameter_table')

        paramdict = single_run._parent_trajectory._exploredparameters
        self._store_single_table(paramdict, paramtable, None,-1)



    ######################################### Storing a Trajectory and a Single Run #####################
    def _store_single_table(self,paramdict,paramtable, creator_name, creator_id):
        ''' Stores a single overview table.

        Called from _store_meta_data and store_single_run
        '''

        assert isinstance(paramtable, pt.Table)


        #print paramtable._v_name

        newrow = paramtable.row
        colnames = set(paramtable.colnames)
        for key, val in paramdict.items():
            if 'size' in colnames:
                newrow['size'] = len(val)

            if 'comment' in colnames:
                newrow['comment'] = val.get_comment()

            if 'location' in colnames:
                newrow['location'] = val.get_location()

            if 'name' in colnames:
                newrow['name'] = val.get_name()

            if 'class_name' in colnames:
                newrow['class_name'] = val.get_class_name()

            if 'value' in colnames:
                valstr = val.to_str()
                if len(valstr) >= globally.HDF5_STRCOL_MAX_NAME_LENGTH:
                    valstr = valstr[0:globally.HDF5_STRCOL_MAX_NAME_LENGTH-1]
                newrow['value'] = valstr

            if 'creator_name' in colnames:
                newrow['creator_name'] = creator_name

            if 'creator_id' in colnames:
                newrow['creator_id'] = creator_id

            #if 'Parent_Trajectory' in colnames:
             #   newrow['Parent_Trajectory'] = self._trajectoryname

            newrow.append()

        paramtable.flush()

    def _store_dict(self, data_dict):
        for key,val in data_dict.items():
            self.store(val)


    def _store_meta_data(self,traj):
        ''' Stores general information about the trajectory in the hdf5file.

        The 'info' table will contain ththane name of the trajectory, it's timestamp, a comment,
        the length (aka the number of single runs), and if applicable a previous trajectory the
        current one was originally loaded from.
        The name of all derived and normal parameters as well as the results are stored in
        appropriate overview tables.
        Thes include the fullname, the name, the name of the class (e.g. SparseParameter),
        the size (1 for single parameter, >1 for explored parameter arrays).
        In case of a derived parameter or a result, the name of the creator trajectory or run
        and the id (-1 for trajectories) are stored.
        '''


        descriptiondict={'name': pt.StringCol(len(traj._name)),
                         'time': pt.StringCol(len(traj._formatted_time)),
                         'timestamp' : pt.FloatCol(),
                         'comment': pt.StringCol(len(traj._comment)),
                         'length':pt.IntCol(),
                         'loaded_from' : pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH)}

        infotable = self._hdf5file.createTable(where=self._trajectorygroup, name='info', description=descriptiondict, title='info')
        newrow = infotable.row
        newrow['name']=traj._name
        newrow['timestamp']=traj._time
        newrow['time']=traj._formatted_time
        newrow['comment']=traj._comment
        newrow['length'] = traj._length
        newrow['loaded_from']=traj._loadedfrom

        newrow.append()
        infotable.flush()


        tostore_dict =  {'config_table':traj._config,
                         'parameter_table':traj._parameters,
                         'derived_parameter_table':traj._derivedparameters,
                         'explored_parameter_table' :traj._exploredparameters,
                         'result_table' : traj._results}

        for key, dictionary in tostore_dict.items():

            paramdescriptiondict={'location': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                  'name': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                  'class_name': pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                  'comment': pt.StringCol(globally.HDF5_STRCOL_MAX_COMMENT_LENGTH)}


            if not key == 'result_table':
                paramdescriptiondict.update({'size' : pt.Int64Col()})
                paramdescriptiondict.update({'value' :pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH)})


            if key in ['derived_parameter_table', 'result_table']:
                paramdescriptiondict.update({'creator_name':pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                             #'Parent_Trajectory':pt.StringCol(globally.HDF5_STRCOL_MAX_NAME_LENGTH),
                                             'creator_id':pt.Int64Col()})

            paramtable = self._hdf5file.createTable(where=self._trajectorygroup, name=key, description=paramdescriptiondict, title=key)

            self._store_single_table(dictionary, paramtable, traj._name,-1)


    def _store_trajectory(self, traj):
        ''' Stores a trajectory to the in __init__ specified hdf5file.
        '''

        self._logger.info('Start storing Trajectory %s.' % self._trajectoryname)

        self._store_meta_data(traj)

        self._store_dict(traj._config)
        self._store_dict(traj._parameters)
        self._store_dict(traj._results)
        self._store_dict(traj._derivedparameters)


        self._logger.info('Finished storing Trajectory.')


    ################# Storing and Loading Parameters ############################################


    def _store_parameter_or_result(self, param,*args,**kwargs):

        fullname = param.get_fullname()
        self._logger.debug('Storing %s.' % fullname)
        store_dict = param._store()


        #self._check_dictionary_structure(store_dict)
        #self._check_info_dict(param, store_dict)

        group= self._create_groups(fullname)



        for key, data_to_store in store_dict.items():
            if isinstance(data_to_store, ObjectTable):
                self._store_into_pytable(key, data_to_store, group, fullname,*args,**kwargs)
            elif isinstance(data_to_store, dict):
                self._store_dict_as_table(key, data_to_store, group, fullname,*args,**kwargs)
            elif isinstance(data_to_store,(list,tuple)) or isinstance(data_to_store,globally.PARAMETER_SUPPORTED_DATA):
                self._store_into_array(key, data_to_store, group, fullname,*args,**kwargs)
            elif isinstance(data_to_store, np.ndarray):
                self._store_into_carray(key, data_to_store, group, fullname,*args,**kwargs)
            elif isinstance(data_to_store,DataFrame):
                self._store_data_frame(key, data_to_store, group, fullname,*args,**kwargs)
            else:
                raise AttributeError('I don not know how to store %s of %s. Cannot handle type %s.'%(key,fullname,str(type(data_to_store))))


    def _store_dict_as_table(self, key, data_to_store, group, fullname,*args,**kwargs):

        if key in group:
            raise ValueError('Dictionary >>%s<< already exists in >>%s<<. Appending is not supported (yet).')


        assert isinstance(data_to_store,dict)

        if key in group:
            raise ValueError('Dict >>%s<< already exists in >>%s<<. Appending is not supported (yet).')



        objtable = ObjectTable(data=data_to_store,index=[0])

        self._store_into_pytable(key,objtable,group,fullname)
        group._f_get_child(key).set_attr('DICT',1)



    def _store_data_frame(self, key, data_to_store, group, fullname,*args,**kwargs):
        try:

            if key in group:
                raise ValueError('DataFrame >>%s<< already exists in >>%s<<. Appending is not supported (yet).')



            assert isinstance(data_to_store,DataFrame)
            assert isinstance(group, pt.Group)

            name = group._v_pathname+'/' +key
            data_to_store.to_hdf(self._filename, name, append=True,data_columns=True)
        except:
            self._logger.error('Failed storing DataFrame >>%s<< of >>%s<<.' %(key,fullname))
            raise




    def _store_into_carray(self, key, data, group, fullname,*args,**kwargs):


        try:
            if key in group:
                raise ValueError('CArray >>%s<< already exists in >>%s<<. Appending is not supported (yet).')




            if isinstance(data, np.ndarray):
                size = data.size
            elif hasattr(data,'__len__'):
                size = len(data)
            else:
                size = 1

            if size == 0:
                self._logger.warning('>>%s<< of >>%s<< is empty, I will skip storing.' %(key,fullname))
                return

            carray=self._hdf5file.create_carray(where=group, name=key,obj=data)
        #carray[:]=data
            self._hdf5file.flush()
        except:
            self._logger.error('Failed storing array >>%s<< of >>%s<<.' % (key, fullname))
            raise


    def _store_into_array(self, key, data, group, fullname,*args,**kwargs):


        try:
            if key in group:
                raise ValueError('Array >>%s<< already exists in >>%s<<. Appending is not supported (yet).')


            if isinstance(data, np.ndarray):
                size = data.size
            elif hasattr(data,'__len__'):
                size = len(data)
            else:
                size = 1

            if size == 0:
                self._logger.warning('>>%s<< of >>%s<< is empty, I will skip storing.' %(key,fullname))
                return


            array=self._hdf5file.create_array(where=group, name=key,obj=data)
            if isinstance(data,tuple):
                array.set_attr('TUPLE',1)
            if isinstance(data, globally.PARAMETER_SUPPORTED_DATA):
                array.set_attr('SCALAR',1)
        #carray[:]=data
            self._hdf5file.flush()
        except:
            self._logger.error('Failed storing array >>%s<< of >>%s<<.' % (key, fullname))
            raise


    def _check_info_dict(self,param, store_dict):
        ''' Checks if the storage dictionary contains an appropriate description of the parameter.
        This entry is called info, and should contain only a single
        :param param: The parameter to store
        :param store_dict: the dictionary that describes how to store the parameter
        '''
        if not 'info' in store_dict:
            store_dict['info']={}

        info_dict = store_dict['info']

        test_item = info_dict.itervalues().next()
        if len(test_item)>1:
            raise AttributeError('Your description of the parameter %s, generated by _store and stored into >>info<< has more than a single dictionary in the list.' % param.get_fullname())


        if not 'name' in info_dict:
            info_dict['name'] = [param.get_name()]
        else:
            assert info_dict['name'][0] == param.get_name()

        if not 'location' in info_dict:
            info_dict['location'] = [param.get_location()]
        else:
            assert info_dict['location'][0] == param.get_location()

        # if not 'comment' in info_dict:
        #     info_dict['comment'] = [param.get_comment()]
        # else:
        #     assert info_dict['comment'][0] == param.get_comment()

        if not 'type' in info_dict:
            info_dict['type'] = [str(type(param))]
        else:
            assert info_dict['type'][0] == str(type(param))


        if not 'class_name' in info_dict:
            info_dict['class_name'] = [param.__class__.__name__]
        else:
            assert info_dict['class_name'][0] == param.__class__.__name__



    def _create_groups(self, key):
        newhdf5group = self._trajectorygroup
        split_key = key.split('.')
        for name in split_key:
            if not name in newhdf5group:
                newhdf5group=self._hdf5file.createGroup(where=newhdf5group, name=name, title=name)
            else:
                newhdf5group = getattr(newhdf5group, name)

        return newhdf5group

    def _store_into_pytable(self,tablename,data,hdf5group,fullname,*args,**kwargs):

        try:
            if hasattr(hdf5group,tablename):
                table = getattr(hdf5group,tablename)

                append_mode = kwargs.pop('append_mode',None)

                if append_mode == HDF5StorageService.APPEND_FULL:
                    nstart = table.nrows
                elif append_mode ==HDF5StorageService.APPEND_PARTS:
                    nstart=0
                else:
                    raise ValueError('Table %s already exists, if you want to append to the table, please use >>append_mode= %s<< or >>append_mode=%s.<<.'
                                     %(tablename,HDF5StorageService.APPEND_FULL,HDF5StorageService.APPEND_PARTS))

                self._logger.debug('Found table %s in file %s, will append new entries in %s to the table.'
                                   % (tablename,self._filename, fullname))

            else:
                description_dict = self._make_description(data,fullname)
                table = self._hdf5file.createTable(where=hdf5group,name=tablename,description=description_dict,
                                                   title=tablename)
                nstart = 0

            assert isinstance(table,pt.Table)
            assert isinstance(data, ObjectTable)


            row = table.row

            datasize = data.shape[0]


            cols = data.columns.tolist()
            for n in range(nstart, datasize):

                for key in cols:
                    row[key] = data[key][n]

                row.append()

            table.flush()
            self._hdf5file.flush()
        except:
            self._logger.error('Failed storing table >>%s<< of >>%s<<.' %(tablename,fullname))
            raise



    def _make_description(self, data, fullname):
        ''' Returns a dictionary that describes a pytbales row.
        '''


        descriptiondict={}

        for key, val in data.iteritems():


            col = self._get_table_col(key, val, fullname)

            # if col is None:
            #     raise TypeError('Entry %s of %s cannot be translated into pytables column' % (key,fullname))

            descriptiondict[key]=col

        return descriptiondict


    def _get_table_col(self, key, column, fullname):
        ''' Creates a pytables column instance.

        The type of column depends on the type of parameter entry.
        '''

        try:
            val = column[0]


            if type(val) == int:
                return pt.IntCol()

            if type(val) == str:
                itemsize = int(self._get_longest_stringsize(column))
                return pt.StringCol(itemsize)

            if isinstance(val, np.ndarray):
                if np.issubdtype(val.dtype,np.str):
                    itemsize = int(self._get_longest_stringsize(column))
                    return pt.StringCol(itemsize,shape=val.shape)
                else:
                    return pt.Col.from_dtype(np.dtype((val.dtype,val.shape)))
            else:
                return pt.Col.from_dtype(np.dtype(type(val)))
        except Exception:
            self._logger.error('Failure in storing >>%s<< of Parameter/Result >>%s<<. Its type was >>%s<<.' % (key,fullname,str(type(val))))
            raise




    def _get_longest_stringsize(self, string_list):
        ''' Returns the longest stringsize for a string entry across data.
        '''
        maxlength = 1

        for stringar in string_list:
            if not isinstance(stringar,np.ndarray):
                stringar = np.array([stringar])
            for string in stringar:
                maxlength = max(len(string),maxlength)

        # Make the string Col longer than needed in order to allow later on slightly large strings
        return maxlength*1.5



    def _load_parameter_or_result(self, param):

        fullname = param.get_fullname()
        self._logger.debug('Loading %s' % fullname)

        try:
            hdf5group = eval('self._trajectorygroup.'+fullname)
        except Exception, e:
            raise AttributeError('ParameterSet %s cannot be found in the hdf5file %s and trajectory %s' % (fullname,self._filename,self._trajectoryname))

        load_dict = {}
        for leaf in hdf5group:
            if isinstance(leaf,pt.Table) and 'DICT' in leaf.attrs and leaf.attrs['DICT']:
                self._read_dictionary(leaf, load_dict)
            elif isinstance(leaf, pt.Table):
                self._read_table(leaf, load_dict)
            elif isinstance(leaf, (pt.CArray,pt.Array)):
                self._read_array(leaf, load_dict)
            elif isinstance(leaf, pt.Group):
                self._read_frame(leaf, load_dict)
            else:
                raise TypeError('Cannot load %s, do not understand the hdf5 file structure of %s.' %(fullname,str(leaf)))


        param._load(load_dict)

    def _read_dictionary(self, leaf, load_dict):
        temp_dict={}


        self._read_table(leaf,temp_dict)
        key =leaf.name
        temp_table = temp_dict[key]
        temp_dict = temp_table.to_dict('list')

        load_dict[key]={}
        for innerkey, vallist in temp_dict.items():
            load_dict[innerkey] = vallist[0]


    def _read_frame(self,group,load_dict):
        name = group._v_name
        pathname = group._v_pathname
        dataframe = read_hdf(self._filename,pathname,mode='r')
        load_dict[name] = dataframe

    def _read_table(self,table,load_dict):
        ''' Reads a non-nested Pytables table column by column.

        :type table: pt.Table
        :type load_dict:
        :return:
        '''

        table_name = table._v_name
        load_dict[table_name]=ObjectTable(columns = table.colnames, index=range(table.nrows))
        for colname in table.colnames:
            col = table.col(colname)
            load_dict[table_name][colname]=list(col)

    def _read_array(self, array, load_dict):

        #assert isinstance(carray,pt.CArray)
        array_name = array._v_name


        if 'TUPLE' in array.attrs and array.attrs['TUPLE']:
            load_dict[array_name] = tuple(array.read())
        else:
            result = array.read()

            ## Numpy Scalars are converted to numpy arrays, but we want to retrieve tha numpy scalar
            # as it was
            if isinstance(result,np.ndarray) and 'SCALAR' in array.attrs and array.attrs['SCALAR']:
                # this is the best way I know to actually restore the original data and not some strange
                # rank 0 scalars
                load_dict[array_name] = np.array([result])[0]
            else:
                load_dict[array_name] = result


