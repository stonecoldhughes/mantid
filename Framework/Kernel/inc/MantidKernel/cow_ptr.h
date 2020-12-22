// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2007 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MultiThreaded.h"

#ifndef Q_MOC_RUN
#include <memory>
#endif

#include <mutex>
#include <vector>

namespace Mantid {
/// typedef for the data storage used in Mantid matrix workspaces
using MantidVec = std::vector<double>;

/// typedef for the pointer to data storage used in Mantid matrix workspaces
using MantidVecPtr = std::shared_ptr<MantidVec>;

} // NAMESPACE Mantid
