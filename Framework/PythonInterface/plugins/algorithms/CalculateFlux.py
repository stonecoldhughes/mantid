# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#     NScD Oak Ridge National Laboratory, European Spallation Source
#     & Institut Laue - Langevin
# SPDX - License - Identifier: GPL - 3.0 +
from __future__ import (absolute_import, division, print_function)
from mantid.api import PythonAlgorithm, MatrixWorkspaceProperty, WorkspaceUnitValidator, HistogramValidator, InstrumentValidator
from mantid.simpleapi import *
from mantid.kernel import Direction, FloatBoundedValidator, CompositeValidator
import numpy as np


class CalculateFlux(PythonAlgorithm):

    def category(self):
        return 'CorrectionFunctions\\NormalisationCorrections'

    def summary(self):
        return 'Calculates the incident beam flux as a function of wavelength using a direct beam SANS data.'

    def name(self):
        return 'CalculateFlux'

    def PyInit(self):
        validator = CompositeValidator()
        validator.add(WorkspaceUnitValidator('Wavelength'))
        validator.add(HistogramValidator())
        validator.add(InstrumentValidator())

        self.declareProperty(MatrixWorkspaceProperty('InputWorkspace', defaultValue='',
                                                     validator = validator,
                                                     direction = Direction.Input),
                             doc='The input workspace in wavelength')

        self.declareProperty('BeamRadius', 0.1, FloatBoundedValidator(lower=0.), 'The radius of the beam [m]')

        self.declareProperty(MatrixWorkspaceProperty('OutputWorkspace',
                                                     defaultValue='',
                                                     direction = Direction.Output),
                             doc='The output workspace')

    def PyExec(self):
        input_ws = self.getProperty('InputWorkspace').value
        wavelengths = input_ws.extractX().flatten()
        min_wavelength = np.min(wavelengths)
        max_wavelength = np.max(wavelengths)
        blocksize = input_ws.blocksize()
        width = (max_wavelength-min_wavelength) / blocksize
        params = [min_wavelength, width, max_wavelength]
        rebinned = Rebin(InputWorkspace=input_ws, StoreInADS=False, Params=params)
        radius = self.getProperty('BeamRadius').value
        shapeXML = '<infinite-cylinder id="flux"><centre x="0.0" y="0.0" z="0.0"/><axis x="0.0" y="0.0" z="1.0"/>' \
                   '<radius val="{0}"/></infinite-cylinder>'.format(radius)
        det_list = FindDetectorsInShape(Workspace=rebinned, ShapeXML=shapeXML)
        output_ws = GroupDetectors(InputWorkspace=rebinned, DetectorList=det_list,
                                   OutputWorkspace=self.getPropertyValue('OutputWorkspace'))
        self.setProperty('OutputWorkspace', output_ws)
AlgorithmFactory.subscribe(CalculateFlux)
