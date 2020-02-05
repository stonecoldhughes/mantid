# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#     NScD Oak Ridge National Laboratory, European Spallation Source
#     & Institut Laue - Langevin
# SPDX - License - Identifier: GPL - 3.0 +
from __future__ import (absolute_import, division, unicode_literals)

from Muon.GUI.Common.utilities.algorithm_utils import run_Fit, run_simultaneous_Fit, run_CalculateMuonAsymmetry
import mantid
from Muon.GUI.Common.ADSHandler.muon_workspace_wrapper import MuonWorkspaceWrapper
from Muon.GUI.Common.ADSHandler.workspace_naming import *
from mantid.simpleapi import (RenameWorkspace, ConvertFitFunctionForMuonTFAsymmetry, CopyLogs, EvaluateFunction)
from mantid.api import AnalysisDataService

MUON_ANALYSIS_SUFFIX = ' MA'
FREQUENCY_DOMAIN_ANALYSIS_SUFFIX = ' FD'
MUON_ANALYSIS_GUESS_WS = '__muon_analysis_fitting_guess'
FREQUENCY_DOMAIN_ANALYSIS_GUESS_WS = '__frequency_domain_analysis_fitting_guess'


class FittingTabModel(object):
    def __init__(self, context):
        self.context = context
        self.function_name = ''
        self.fit_function = None
        self.fit_type = "Single"
        self.fit_by = "None"
        self.time_range = [0.11, 15]
        self.fitting_attributes = {}

    @property
    def function_name(self):
        return self._function_name

    @function_name.setter
    def function_name(self, value):
        if value:
            self._function_name = ' ' + value
        else:
            self._function_name = ''

    def do_single_fit(self, parameter_dict, add_fit_to_context=True):
        output_workspace, fitting_parameters_table, function_object, output_status, output_chi_squared, covariance_matrix = \
            self.do_single_fit_and_return_workspace_parameters_and_fit_function(parameter_dict)

        self._handle_single_fit_results(parameter_dict['InputWorkspace'], function_object, fitting_parameters_table,
                                        output_workspace, covariance_matrix, add_fit_to_context)

        return function_object.clone(), output_status, output_chi_squared

    def evaluate_single_fit(self, workspaces, add_fit_to_context=True):

        params = {}
        params['Minimizer'] = 'Levenberg-Marquardt'
        params['EvaluationType'] = 'CentrePoint'
        params['Function'] = self.fit_function

        if self.fit_type == "Single":
            params['InputWorkspace'] = workspaces[0]
            params['StartX'] = 0.11
            params['EndX'] = 15
            function_object, output_status, output_chi_squared = self.do_single_fit(params,
                                                                                    add_fit_to_context)
        else:
            params['InputWorkspace'] = workspaces
            params['StartX'] = [0.11] * len(workspaces)
            params['EndX'] = [15] * len(workspaces)
            function_object, output_status, output_chi_squared = self.do_simultaneous_fit(params,
                                                                                          [],
                                                                                          add_fit_to_context)

        return function_object, output_status, output_chi_squared

    def do_single_tf_fit(self, parameter_dict):
        alg = mantid.AlgorithmManager.create("CalculateMuonAsymmetry")
        output_workspace, fitting_parameters_table, function_object, output_status, output_chi_squared, covariance_matrix = \
            run_CalculateMuonAsymmetry(parameter_dict, alg)
        CopyLogs(InputWorkspace=parameter_dict['ReNormalizedWorkspaceList'], OutputWorkspace=output_workspace,
                 StoreInADS=False)
        self._handle_single_fit_results(parameter_dict['ReNormalizedWorkspaceList'], function_object,
                                        fitting_parameters_table, output_workspace, covariance_matrix)

        return function_object.clone(), output_status, output_chi_squared

    def do_single_fit_and_return_workspace_parameters_and_fit_function(
            self, parameters_dict):
        alg = mantid.AlgorithmManager.create("Fit")
        output_workspace, output_parameters, function_object, output_status, output_chi, covariance_matrix = run_Fit(
            parameters_dict, alg)
        CopyLogs(InputWorkspace=parameters_dict['InputWorkspace'], OutputWorkspace=output_workspace, StoreInADS=False)
        return output_workspace, output_parameters, function_object, output_status, output_chi, covariance_matrix

    def _handle_single_fit_results(self, input_workspace, fit_function, fitting_parameters_table, output_workspace,
                                   covariance_matrix, add_to_context=True):
        workspace_name, workspace_directory = self.create_fitted_workspace_name(input_workspace, fit_function)
        table_name, table_directory = self.create_parameter_table_name(input_workspace, fit_function)

        self.add_workspace_to_ADS(output_workspace, workspace_name, workspace_directory)
        self.add_workspace_to_ADS(covariance_matrix, workspace_name + '_CovarianceMatrix', table_directory)
        wrapped_parameter_workspace = self.add_workspace_to_ADS(fitting_parameters_table, table_name, table_directory)
        if add_to_context:
            self.add_fit_to_context(wrapped_parameter_workspace,
                                    fit_function,
                                    input_workspace, [workspace_name])

    def do_simultaneous_fit(self, parameter_dict, global_parameters, add_to_context=True):
        output_workspace, fitting_parameters_table, function_object, output_status, output_chi_squared, covariance_matrix = \
            self.do_simultaneous_fit_and_return_workspace_parameters_and_fit_function(parameter_dict)

        self._handle_simultaneous_fit_results(parameter_dict['InputWorkspace'], function_object,
                                              fitting_parameters_table, output_workspace, global_parameters,
                                              covariance_matrix, add_to_context)

        return function_object, output_status, output_chi_squared

    def do_simultaneous_fit_and_return_workspace_parameters_and_fit_function(
            self, parameters_dict):
        alg = mantid.AlgorithmManager.create("Fit")

        output_workspace, output_parameters, function_object, output_status, output_chi, covariance_matrix \
            = run_simultaneous_Fit(parameters_dict, alg)
        if len(parameters_dict['InputWorkspace']) > 1:
            for input_workspace, output in zip(parameters_dict['InputWorkspace'],
                                               mantid.api.AnalysisDataService.retrieve(output_workspace).getNames()):
                CopyLogs(InputWorkspace=input_workspace, OutputWorkspace=output, StoreInADS=False)
        else:
            CopyLogs(InputWorkspace=parameters_dict['InputWorkspace'][0], OutputWorkspace=output_workspace,
                     StoreInADS=False)
        return output_workspace, output_parameters, function_object, output_status, output_chi, covariance_matrix

    def do_simultaneous_tf_fit(self, parameter_dict, global_parameters, add_to_context=True):
        alg = mantid.AlgorithmManager.create("CalculateMuonAsymmetry")
        output_workspace, fitting_parameters_table, function_object, output_status, output_chi_squared, covariance_matrix = \
            run_CalculateMuonAsymmetry(parameter_dict, alg)
        if len(parameter_dict['ReNormalizedWorkspaceList']) > 1:
            for input_workspace, output in zip(parameter_dict['ReNormalizedWorkspaceList'],
                                               mantid.api.AnalysisDataService.retrieve(output_workspace).getNames()):
                CopyLogs(InputWorkspace=input_workspace, OutputWorkspace=output, StoreInADS=False)
        else:
            CopyLogs(InputWorkspace=parameter_dict['ReNormalizedWorkspaceList'][0], OutputWorkspace=output_workspace,
                     StoreInADS=False)

        self._handle_simultaneous_fit_results(parameter_dict['ReNormalizedWorkspaceList'], function_object,
                                              fitting_parameters_table, output_workspace, global_parameters,
                                              covariance_matrix, add_to_context)

        return function_object, output_status, output_chi_squared

    def evaluate_sequential_fit(self, workspaces, add_fit_to_context=True):
        params = {}
        params['Minimizer'] = 'Levenberg-Marquardt'
        params['EvaluationType'] = 'CentrePoint'
        params['Function'] = self.fit_function

        # workspaces are stored as list of list [[Fit1 workspaces], [Fit2 workspaces], [Fit3 workspaces]]
        if self.fit_type == "Single":
            # flatten the workspace list
            params['InputWorkspace'] = [workspace for fit_workspaces in workspaces for workspace in fit_workspaces]
            params['StartX'] = 0.11
            params['EndX'] = 15
            function_object, output_status, output_chi_squared = self.do_sequential_fit(params, add_fit_to_context)
        else:
            # in a simultaneous-sequential fit, each fit corresponds to a list of workspaces
            params['InputWorkspace'] = workspaces
            params['StartX'] = [0.11]
            params['EndX'] = [15]
            function_object, output_status, output_chi_squared = self.do_sequential_simultaneous_fit(params,
                                                                                                     add_fit_to_context)

        return function_object, output_status, output_chi_squared

    def do_sequential_fit(self, parameter_dict, add_fit_to_context=True):
        function_object_list = []
        output_status_list = []
        output_chi_squared_list = []
        function_object = parameter_dict['Function']

        for input_workspace in parameter_dict['InputWorkspace']:
            sub_parameter_dict = parameter_dict.copy()
            sub_parameter_dict['InputWorkspace'] = input_workspace
            sub_parameter_dict['Function'] = function_object

            function_object, output_status, output_chi_squared = self.do_single_fit(sub_parameter_dict,
                                                                                    add_fit_to_context)
            # This is required so that a new function object is created that is not overwritten in subsequent iterations
            new_function = function_object.clone()
            function_object_list.append(new_function)

            output_status_list.append(output_status)
            output_chi_squared_list.append(output_chi_squared)

        return function_object_list, output_status_list, output_chi_squared_list

    def do_sequential_simultaneous_fit(self, parameter_dict, add_fit_to_context):
        function_object_list = []
        output_status_list = []
        output_chi_squared_list = []
        function_object = parameter_dict['Function']

        for input_workspaces in parameter_dict['InputWorkspace']:
            sub_parameter_dict = parameter_dict.copy()
            sub_parameter_dict['InputWorkspace'] = input_workspaces
            sub_parameter_dict['Function'] = function_object
            sub_parameter_dict['StartX'] = [0.11]*len(input_workspaces)
            sub_parameter_dict['EndX'] = [15]*len(input_workspaces)

            function_object, output_status, output_chi_squared = self.do_simultaneous_fit(sub_parameter_dict,
                                                                                          [], add_fit_to_context)
            # This is required so that a new function object is created that is not overwritten in subsequent iterations
            new_function = function_object.clone()
            function_object_list.append(new_function)

            output_status_list.append(output_status)
            output_chi_squared_list.append(output_chi_squared)

        return function_object_list, output_status_list, output_chi_squared_list

    def do_sequential_tf_fit(self, parameter_dict, output_workspace_group):
        function_object_list = []
        output_status_list = []
        output_chi_squared_list = []
        function_object = parameter_dict['InputFunction']
        for input_workspace, un_normalised_workspace, fit_name in zip(parameter_dict['ReNormalizedWorkspaceList'],
                                                                      parameter_dict['UnNormalizedWorkspaceList'],
                                                                      parameter_dict['OutputFitWorkspace']):
            sub_parameter_dict = parameter_dict.copy()
            sub_parameter_dict['ReNormalizedWorkspaceList'] = input_workspace
            sub_parameter_dict['UnNormalizedWorkspaceList'] = un_normalised_workspace
            sub_parameter_dict['OutputFitWorkspace'] = fit_name
            sub_parameter_dict['InputFunction'] = function_object

            function_object, output_status, output_chi_squared = self.do_single_tf_fit(sub_parameter_dict,
                                                                                       output_workspace_group)
            # This is required so that a new function object is created that is not overwritten in subsequent iterations
            new_function = function_object.clone()
            function_object_list.append(new_function)

            output_status_list.append(output_status)
            output_chi_squared_list.append(output_chi_squared)

        return function_object_list, output_status_list, output_chi_squared_list

    def calculate_tf_function(self, algorithm_parameters):
        return ConvertFitFunctionForMuonTFAsymmetry(StoreInADS=False, **algorithm_parameters)

    def _handle_simultaneous_fit_results(self, input_workspace_list, fit_function, fitting_parameters_table,
                                         output_workspace, global_parameters, covariance_matrix, add_to_context=True):
        if len(input_workspace_list) > 1:
            table_name, table_directory = self.create_parameter_table_name(input_workspace_list[0] + '+ ...',
                                                                           fit_function)
            workspace_name, workspace_directory = self.create_multi_domain_fitted_workspace_name(
                input_workspace_list[0], fit_function)
            self.add_workspace_to_ADS(output_workspace, workspace_name, '')

            workspace_name = self.rename_members_of_fitted_workspace_group(workspace_name,
                                                                           input_workspace_list,
                                                                           fit_function)
            self.add_workspace_to_ADS(covariance_matrix, workspace_name[0] + '_CovarianceMatrix', table_directory)
        else:
            table_name, table_directory = self.create_parameter_table_name(input_workspace_list[0], fit_function)
            workspace_name, workspace_directory = self.create_fitted_workspace_name(input_workspace_list[0],
                                                                                    fit_function)
            self.add_workspace_to_ADS(output_workspace, workspace_name, workspace_directory)
            self.add_workspace_to_ADS(covariance_matrix, workspace_name + '_CovarianceMatrix', table_directory)
            workspace_name = [workspace_name]

        wrapped_parameter_workspace = self.add_workspace_to_ADS(fitting_parameters_table, table_name,
                                                                table_directory)

        if add_to_context:
            self.add_fit_to_context(wrapped_parameter_workspace,
                                    fit_function,
                                    input_workspace_list,
                                    workspace_name,
                                    global_parameters)

    def rename_members_of_fitted_workspace_group(self, group_workspace, inputworkspace_list, function):
        self.context.ads_observer.observeRename(False)
        output_workspace_list = []
        for index, workspace_name in enumerate(AnalysisDataService.retrieve(group_workspace).getNames()):
            new_name, _ = self.create_fitted_workspace_name(inputworkspace_list[index], function)

            new_name += '; Simultaneous'
            output_workspace_list.append(new_name)
            RenameWorkspace(InputWorkspace=workspace_name,
                            OutputWorkspace=new_name)

        self.context.ads_observer.observeRename(True)

        return output_workspace_list

    def add_workspace_to_ADS(self, workspace, name, directory):
        self.context.ads_observer.observeRename(False)
        workspace_wrapper = MuonWorkspaceWrapper(workspace)
        workspace_wrapper.show(directory + name)
        self.context.ads_observer.observeRename(True)
        return workspace_wrapper

    def create_fitted_workspace_name(self, input_workspace_name, function_name):
        directory = input_workspace_name + '; Fitted;' + self.function_name + '/'
        name = input_workspace_name + '; Fitted;' + self.function_name + '; Workspace'

        return name, directory

    def create_multi_domain_fitted_workspace_name(self, input_workspace, function):
        directory = input_workspace + '; Fitted;' + self.function_name + '/'
        name = input_workspace + '+ ...; Fitted;' + self.function_name

        return name, directory

    def create_parameter_table_name(self, input_workspace_name, function_name):
        directory = input_workspace_name + '; Fitted;' + self.function_name + '/'
        name = input_workspace_name + '; Fitted Parameters;' + self.function_name

        return name, directory

    def get_function_name(self, function):
        if function is None:
            return ''

        if function.getNumberDomains() > 1:
            function_temp = function.getFunction(0)
        else:
            function_temp = function

        try:
            function_string_list = []
            for i in range(function_temp.nFunctions()):
                function_string_list.append(function_temp.getFunction(i).name())
            if len(function_string_list) > 3:
                function_string_list = function_string_list[:3]
                function_string_list.append('...')
            function_string = ','.join(function_string_list)
            return function_string
        except AttributeError:
            return function_temp.name()

    def add_fit_to_context(self, parameter_workspace, function,
                           input_workspace, output_workspace_name, global_parameters=None):
        self.context.fitting_context.add_fit_from_values(
            parameter_workspace, self.function_name,
            input_workspace, output_workspace_name, global_parameters)

    def change_plot_guess(self, plot_guess, parameter_dict):
        try:
            fit_function = parameter_dict['Function']
            data_ws_name = parameter_dict['InputWorkspace']
        except KeyError:
            return
        if self.context.workspace_suffix == MUON_ANALYSIS_SUFFIX:
            guess_ws_name = MUON_ANALYSIS_GUESS_WS
        elif self.context.workspace_suffix == FREQUENCY_DOMAIN_ANALYSIS_SUFFIX:
            guess_ws_name = FREQUENCY_DOMAIN_ANALYSIS_GUESS_WS
        else:
            guess_ws_name = '__unknown_interface_fitting_guess'

        # Handle case of function removed
        if fit_function is None and plot_guess:
            self.context.fitting_context.notify_plot_guess_changed(plot_guess, None)
        elif fit_function is None or data_ws_name == '':
            return
        else:
            # evaluate the current function on the workspace
            if plot_guess:
                try:
                    EvaluateFunction(InputWorkspace=data_ws_name,
                                     Function=fit_function,
                                     StartX=parameter_dict['StartX'],
                                     EndX=parameter_dict['EndX'],
                                     OutputWorkspace=guess_ws_name)
                except RuntimeError:
                    mantid.logger.error('Could not evaluate the function.')
                    return

            if AnalysisDataService.doesExist(guess_ws_name):
                self.context.fitting_context.notify_plot_guess_changed(plot_guess, guess_ws_name)

    def get_selected_workspace_list(self):
        selected_workspaces = []
        selected_groups_and_pairs = self._get_selected_groups_and_pairs()
        for grp_and_pair in selected_groups_and_pairs:
            selected_workspaces += self.context.get_names_of_workspaces_to_fit(
                runs='All',
                group_and_pair=grp_and_pair,
                phasequad=False,
                rebin=False, freq="None")
        return selected_workspaces

    def get_runs_groups_and_pairs_for_fits(self):
        selected_workspaces = self.get_selected_workspace_list()
        runs = []
        groups_and_pairs = []

        if self.fit_type == "Single":
            for workspace in selected_workspaces:
                runs += [get_run_number_from_workspace_name(workspace, self.context.data_context.instrument)]
                groups_and_pairs += [get_group_or_pair_from_name(workspace)]
        else:
            fit_workspaces = {}
            if self.fit_by == "Run":
                for workspace in selected_workspaces:
                    run = get_run_number_from_workspace_name(workspace, self.context.data_context.instrument)
                    if run not in fit_workspaces:
                        fit_workspaces[run] = get_group_or_pair_from_name(workspace)
                    else:
                        fit_workspaces[run] += ";" + get_group_or_pair_from_name(workspace)
                runs = list(fit_workspaces.keys())
                groups_and_pairs = list(fit_workspaces.values())
            elif self.fit_by == "Group/Pair":
                for workspace in selected_workspaces:
                    group_or_pair = get_group_or_pair_from_name(workspace)
                    run = get_run_number_from_workspace_name(workspace, self.context.data_context.instrument)
                    if group_or_pair not in fit_workspaces:
                        fit_workspaces[group_or_pair] = run
                    else:
                        fit_workspaces[group_or_pair] += ";" + run
                runs = list(fit_workspaces.values())
                groups_and_pairs = list(fit_workspaces.keys())
            else:
                return

        return runs, groups_and_pairs

    def get_workspace_names_from_group_and_run(self, run, group_or_pair):
        if group_or_pair in self.context.group_pair_context.selected_pairs:
            workspace_name = get_pair_asymmetry_name(self.context, group_or_pair, run, False)
        else:
            workspace_name = get_group_asymmetry_name(self.context, group_or_pair, run, False)

        return workspace_name

    def get_fit_workspace_names_from_groups_and_runs(self, runs, groups_and_pairs):
        workspace_names = []
        for run in runs:
            for group_or_pair in groups_and_pairs:
                if group_or_pair in self.context.group_pair_context.selected_pairs:
                    workspace_names += [get_pair_asymmetry_name(self.context, group_or_pair, run, False)]
                else:
                    workspace_names += [get_group_asymmetry_name(self.context, group_or_pair, run, False)]

            return workspace_names

    def _get_selected_groups_and_pairs(self):
        return self.context.group_pair_context.selected_groups + self.context.group_pair_context.selected_pairs

    def update_stored_fit_function(self, fit_function):
        self.fit_function = fit_function

    def update_fitting_attributes(self, minimizer, evaluation_type):
        self.fitting_attributes.clear()
        self.fitting_attributes['Minimizer'] = minimizer
        self.fitting_attributes['EvaluationType'] = evaluation_type

    def update_model_from_view(self, fit_type, fit_specifier="None"):
        self.fit_type = fit_type
        self.fit_by = fit_specifier
