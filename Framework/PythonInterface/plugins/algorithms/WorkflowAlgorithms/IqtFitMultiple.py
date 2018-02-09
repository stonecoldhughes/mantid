from __future__ import (absolute_import, division, print_function)

from mantid import logger, AlgorithmFactory
from mantid.api import *
from mantid.kernel import *
import mantid.simpleapi as ms


class IqtFitMultiple(PythonAlgorithm):
    _input_ws = None
    _function = None
    _fit_type = None
    _start_x = None
    _end_x = None
    _spec_min = None
    _spec_max = None
    _intensities_constrained = None
    _minimizer = None
    _max_iterations = None
    _result_name = None
    _parameter_name = None
    _fit_group_name = None

    def category(self):
        return "Workflow\\MIDAS"

    def summary(self):

        return "Fits an \*\_iqt file generated by I(Q,t)."

    def PyInit(self):
        self.declareProperty(MatrixWorkspaceProperty('InputWorkspace', '', direction=Direction.Input),
                             doc='The _iqt.nxs InputWorkspace used by the algorithm')

        self.declareProperty(name='Function', defaultValue='',
                             doc='The function to use in fitting')

        self.declareProperty(name='FitType', defaultValue='',
                             doc='The type of fit being carried out')

        self.declareProperty(name='StartX', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc="The first value for X")

        self.declareProperty(name='EndX', defaultValue=0.2,
                             validator=FloatBoundedValidator(0.0),
                             doc="The last value for X")

        self.declareProperty(name='SpecMin', defaultValue=0,
                             validator=IntBoundedValidator(0),
                             doc='Minimum spectra in the workspace to fit')

        self.declareProperty(name='SpecMax', defaultValue=1,
                             validator=IntBoundedValidator(0),
                             doc='Maximum spectra in the workspace to fit')

        self.declareProperty(name='Minimizer', defaultValue='Levenberg-Marquardt',
                             doc='The minimizer to use in fitting')

        self.declareProperty(name="MaxIterations", defaultValue=500,
                             validator=IntBoundedValidator(0),
                             doc="The Maximum number of iterations for the fit")

        self.declareProperty(name='ConstrainIntensities', defaultValue=False,
                             doc="If the Intensities should be constrained during the fit")

        self.declareProperty(name='ExtractMembers', defaultValue=False,
                             doc="If true, then each member of the fit will be extracted, into their"
                                 "own workspace. These workspaces will have a histogram for each spectrum "
                                 "(Q-value) and will be grouped.")

        self.declareProperty(MatrixWorkspaceProperty('OutputResultWorkspace', '', direction=Direction.Output),
                             doc='The output workspace containing the results of the fit data')

        self.declareProperty(ITableWorkspaceProperty('OutputParameterWorkspace', '', direction=Direction.Output),
                             doc='The output workspace containing the parameters for each fit')

        self.declareProperty(WorkspaceGroupProperty('OutputWorkspaceGroup', '', direction=Direction.Output),
                             doc='The OutputWorkspace group Data, Calc and Diff, values for the fit of each spectra')

    def validateInputs(self):
        self._get_properties()
        issues = dict()

        maximum_possible_spectra = self._input_ws.getNumberHistograms()
        maximum_possible_x = self._input_ws.readX(0)[self._input_ws.blocksize() - 1]
        # Validate SpecMin/Max

        if self._spec_max > maximum_possible_spectra:
            issues['SpecMax'] = ('SpecMax must be smaller or equal to the number of '
                                 'spectra in the input workspace, %d' % maximum_possible_spectra)
        if self._spec_min < 0:
            issues['SpecMin'] = 'SpecMin can not be less than 0'
        if self._spec_max < self._spec_min:
            issues['SpecMax'] = 'SpecMax must be more than or equal to SpecMin'

        # Validate Start/EndX
        if self._end_x > maximum_possible_x:
            issues['EndX'] = ('EndX must be less than the highest x value in the workspace, %d' % maximum_possible_x)
        if self._start_x < 0:
            issues['StartX'] = 'StartX can not be less than 0'
        if self._start_x > self._end_x:
            issues['EndX'] = 'EndX must be more than StartX'

        return issues

    def _get_properties(self):
        self._input_ws = self.getProperty('InputWorkspace').value
        self._function = self.getProperty('Function').value
        self._fit_type = self.getProperty('FitType').value
        self._start_x = self.getProperty('StartX').value
        self._end_x = self.getProperty('EndX').value
        self._spec_min = self.getProperty('SpecMin').value
        self._spec_max = self.getProperty('SpecMax').value
        self._intensities_constrained = self.getProperty('ConstrainIntensities').value
        self._do_extract_members = self.getProperty('ExtractMembers').value
        self._minimizer = self.getProperty('Minimizer').value
        self._max_iterations = self.getProperty('MaxIterations').value
        self._result_name = self.getPropertyValue('OutputResultWorkspace')
        self._parameter_name = self.getPropertyValue('OutputParameterWorkspace')
        self._fit_group_name = self.getPropertyValue('OutputWorkspaceGroup')

    def PyExec(self):
        from IndirectCommon import (convertToElasticQ,
                                    transposeFitParametersTable)

        setup_prog = Progress(self, start=0.0, end=0.1, nreports=4)
        setup_prog.report('generating output name')
        output_workspace = self._fit_group_name
        # check if the naming convention used is already correct
        chopped_name = self._fit_group_name.split('_')
        if 'WORKSPACE' in chopped_name[-1].upper():
            output_workspace = '_'.join(chopped_name[:-1])

        option = self._fit_type[:-2]
        logger.information('Option: ' + option)
        logger.information('Function: ' + self._function)

        setup_prog.report('Cropping workspace')
        # prepare input workspace for fitting
        tmp_fit_workspace = "__Iqtfit_fit_ws"
        if self._spec_max is None:
            crop_alg = self.createChildAlgorithm("CropWorkspace", enableLogging=False)
            crop_alg.setProperty("InputWorkspace", self._input_ws)
            crop_alg.setProperty("OutputWorkspace", tmp_fit_workspace)
            crop_alg.setProperty("XMin", self._start_x)
            crop_alg.setProperty("XMax", self._end_x)
            crop_alg.setProperty("StartWorkspaceIndex", self._spec_min)
            crop_alg.execute()
        else:
            crop_alg = self.createChildAlgorithm("CropWorkspace", enableLogging=False)
            crop_alg.setProperty("InputWorkspace", self._input_ws)
            crop_alg.setProperty("OutputWorkspace", tmp_fit_workspace)
            crop_alg.setProperty("XMin", self._start_x)
            crop_alg.setProperty("XMax", self._end_x)
            crop_alg.setProperty("StartWorkspaceIndex", self._spec_min)
            crop_alg.setProperty("EndWorkspaceIndex", self._spec_max)
            crop_alg.execute()

        setup_prog.report('Converting to Histogram')
        convert_to_hist_alg = self.createChildAlgorithm("ConvertToHistogram", enableLogging=False)
        convert_to_hist_alg.setProperty("InputWorkspace", crop_alg.getProperty("OutputWorkspace").value)
        convert_to_hist_alg.setProperty("OutputWorkspace", tmp_fit_workspace)
        convert_to_hist_alg.execute()
        mtd.addOrReplace(tmp_fit_workspace, convert_to_hist_alg.getProperty("OutputWorkspace").value)
        setup_prog.report('Convert to Elastic Q')
        convertToElasticQ(tmp_fit_workspace)

        # fit multi-domain function to workspace
        fit_prog = Progress(self, start=0.1, end=0.8, nreports=2)
        multi_domain_func, kwargs = self._create_mutli_domain_func(self._function, tmp_fit_workspace)
        fit_prog.report('Fitting...')
        ms.Fit(Function=multi_domain_func,
               InputWorkspace=tmp_fit_workspace,
               WorkspaceIndex=0,
               Output=output_workspace,
               CreateOutput=True,
               Minimizer=self._minimizer,
               MaxIterations=self._max_iterations,
               **kwargs)
        fit_prog.report('Fitting complete')

        conclusion_prog = Progress(self, start=0.8, end=1.0, nreports=5)
        conclusion_prog.report('Renaming workspaces')
        # rename workspaces to match user input
        rename_alg = self.createChildAlgorithm("RenameWorkspace", enableLogging=False)
        if output_workspace + "_Workspaces" != self._fit_group_name:
            rename_alg.setProperty("InputWorkspace", output_workspace + "_Workspaces")
            rename_alg.setProperty("OutputWorkspace", self._fit_group_name)
            rename_alg.execute()
        if output_workspace + "_Parameters" != self._parameter_name:
            rename_alg.setProperty("InputWorkspace", output_workspace + "_Parameters")
            rename_alg.setProperty("OutputWorkspace", self._parameter_name)
            rename_alg.execute()
        conclusion_prog.report('Transposing parameter table')
        transposeFitParametersTable(self._parameter_name)

        # set first column of parameter table to be axis values
        x_axis = mtd[tmp_fit_workspace].getAxis(1)
        axis_values = x_axis.extractValues()
        for i, value in enumerate(axis_values):
            mtd[self._parameter_name].setCell('axis-1', i, value)

        # convert parameters to matrix workspace
        parameter_names = 'A0,Height,Lifetime,Stretching'
        conclusion_prog.report('Processing indirect fit parameters')
        pifp_alg = self.createChildAlgorithm("ProcessIndirectFitParameters")
        pifp_alg.setProperty("InputWorkspace", self._parameter_name)
        pifp_alg.setProperty("ColumnX", "axis-1")
        pifp_alg.setProperty("XAxisUnit", "MomentumTransfer")
        pifp_alg.setProperty("ParameterNames", parameter_names)
        pifp_alg.setProperty("OutputWorkspace", self._result_name)
        pifp_alg.execute()
        result_workspace = pifp_alg.getProperty("OutputWorkspace").value

        mtd.addOrReplace(self._result_name, result_workspace)

        # create and add sample logs
        sample_logs = {'start_x': self._start_x, 'end_x': self._end_x, 'fit_type': self._fit_type[:-2],
                       'intensities_constrained': self._intensities_constrained, 'beta_constrained': True}

        conclusion_prog.report('Copying sample logs')
        copy_log_alg = self.createChildAlgorithm("CopyLogs", enableLogging=False)
        copy_log_alg.setProperty("InputWorkspace", self._input_ws)
        copy_log_alg.setProperty("OutputWorkspace", result_workspace)
        copy_log_alg.execute()
        copy_log_alg.setProperty("InputWorkspace", self._input_ws)
        copy_log_alg.setProperty("OutputWorkspace", self._fit_group_name)
        copy_log_alg.execute()

        log_names = [item for item in sample_logs]
        log_values = [sample_logs[item] for item in sample_logs]

        conclusion_prog.report('Adding sample logs')
        add_sample_log_multi = self.createChildAlgorithm("AddSampleLogMultiple", enableLogging=False)
        add_sample_log_multi.setProperty("Workspace", result_workspace.name())
        add_sample_log_multi.setProperty("LogNames", log_names)
        add_sample_log_multi.setProperty("LogValues", log_values)
        add_sample_log_multi.execute()
        add_sample_log_multi.setProperty("Workspace", self._fit_group_name)
        add_sample_log_multi.setProperty("LogNames", log_names)
        add_sample_log_multi.setProperty("LogValues", log_values)
        add_sample_log_multi.execute()

        delete_alg = self.createChildAlgorithm("DeleteWorkspace", enableLogging=False)
        delete_alg.setProperty("Workspace", tmp_fit_workspace)
        delete_alg.execute()

        if self._do_extract_members:
            ms.ExtractQENSMembers(InputWorkspace=self._input_ws,
                                  ResultWorkspace=self._fit_group_name,
                                  OutputWorkspace=self._fit_group_name.rsplit('_')[0] + "_Members")

        self.setProperty('OutputResultWorkspace', result_workspace)
        self.setProperty('OutputParameterWorkspace', self._parameter_name)
        self.setProperty('OutputWorkspaceGroup', self._fit_group_name)
        conclusion_prog.report('Algorithm complete')

    def _create_mutli_domain_func(self, function, input_ws):
        multi = 'composite=MultiDomainFunction,NumDeriv=true;'
        comp = '(composite=CompositeFunction,NumDeriv=true,$domains=i;' + function + ');'

        ties = []
        kwargs = {}
        num_spectra = mtd[input_ws].getNumberHistograms()
        for i in range(0, num_spectra):
            multi += comp
            kwargs['WorkspaceIndex_' + str(i)] = i

            if i > 0:
                kwargs['InputWorkspace_' + str(i)] = input_ws

                # tie beta for every spectrum
                tie = 'f%d.f1.Stretching=f0.f1.Stretching' % i
                ties.append(tie)

        ties = ','.join(ties)
        multi += 'ties=(' + ties + ')'

        return multi, kwargs


AlgorithmFactory.subscribe(IqtFitMultiple)
