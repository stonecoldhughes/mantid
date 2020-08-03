// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidAPI/IFileLoader.h"
#include "MantidDataHandling/LoadHelper.h"
#include "MantidKernel/NexusDescriptor.h"
#include "MantidKernel/System.h"
#include "MantidNexus/NexusClasses.h"

#include <H5Cpp.h>

namespace Mantid {
namespace DataHandling {

class DLLExport LoadILLSANS2
    : public API::IFileLoader<Kernel::NexusDescriptor> {
public:
  const std::string name() const override;
  const std::string summary() const override;
  int version() const override;
  const std::vector<std::string> seeAlso() const override {
    return {"LoadNexus"};
  }
  const std::string category() const override;
  /// Returns a confidence value that this algorithm can load a file
  int confidence(Kernel::NexusDescriptor &descriptor) const override;

private:
  void init() override;
  void exec() override;
  void loadData(const std::vector<std::vector<double>> &,
                API::MatrixWorkspace_sptr, const double);
  API::MatrixWorkspace_sptr createEmptyWorkspace(const size_t, const size_t);
  void runLoadInstrument(API::MatrixWorkspace_sptr);
  double getScalarEntry(H5::H5File &, const std::string &entry);
  std::pair<double, double> getTwoScalarEntry(H5::H5File &, const std::string &entry);
  void moveDetectorDistance(double, API::MatrixWorkspace_sptr,
                            const std::string &);
  Kernel::V3D getComponentPosition(API::MatrixWorkspace_sptr, const std::string &componentName);
  void setPixelSize(API::MatrixWorkspace_sptr);
};

} // namespace DataHandling
} // namespace Mantid
