# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=invalid-name
from Muon.GUI.ElementalAnalysis2.elemental_analysis import ElementalAnalysisGui
from interface_launcher import open_interface

name = "Elemental_Analysis_2"
open_interface(ElementalAnalysisGui, name)
