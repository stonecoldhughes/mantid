// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +

#include "MantidDataHandling/LoadILLSANS2.h"
#include "MantidAPI/Axis.h"
#include "MantidAPI/FileProperty.h"
#include "MantidAPI/MatrixWorkspace.h"
#include "MantidAPI/Progress.h"
#include "MantidAPI/RegisterFileLoader.h"
#include "MantidAPI/SpectrumInfo.h"
#include "MantidAPI/WorkspaceFactory.h"
#include "MantidGeometry/IDetector.h"
#include "MantidGeometry/Instrument.h"
#include "MantidGeometry/Instrument/RectangularDetector.h"
#include "MantidHistogramData/LinearGenerator.h"
#include "MantidKernel/ConfigService.h"
#include "MantidKernel/OptionalBool.h"
#include "MantidKernel/PhysicalConstants.h"
#include "MantidKernel/UnitFactory.h"
#include "MantidKernel/VectorHelper.h"

#include <H5Cpp.h>

namespace Mantid {
namespace DataHandling {

using namespace Kernel;
using namespace API;
using namespace NeXus;
using namespace H5;

// Register the algorithm into the AlgorithmFactory
DECLARE_NEXUS_FILELOADER_ALGORITHM(LoadILLSANS2)

//----------------------------------------------------------------------------------------------

/// Algorithms name for identification. @see Algorithm::name
const std::string LoadILLSANS2::name() const { return "LoadILLSANS"; }

/// Algorithm's version for identification. @see Algorithm::version
int LoadILLSANS2::version() const { return 2; }

/// Algorithm's category for identification. @see Algorithm::category
const std::string LoadILLSANS2::category() const {
  return "DataHandling\\Nexus;ILL\\SANS";
}

/// Algorithm's summary for use in the GUI and help. @see Algorithm::summary
const std::string LoadILLSANS2::summary() const {
  return "This is a mock loader for grasp simulated D22 nexus files.";
}

//----------------------------------------------------------------------------------------------

/**
 * Return the confidence with with this algorithm can load the file
 * @param descriptor A descriptor for the file
 * @returns An integer specifying the confidence level. 0 indicates it will not
 * be used
 */
int LoadILLSANS2::confidence(Kernel::NexusDescriptor &descriptor) const {
  if (descriptor.pathExists("/entry0/d22/detector"))
  {
    return 80;
  } else {
    return 0;
  }
}


//----------------------------------------------------------------------------------------------
/** Initialize the algorithm's properties.
 */
void LoadILLSANS2::init() {
  declareProperty(std::make_unique<FileProperty>("Filename", "",
                                                 FileProperty::Load, ".nxs"),
                  "Name of the nexus file to load");
  declareProperty(std::make_unique<WorkspaceProperty<>>("OutputWorkspace", "",
                                                        Direction::Output),
                  "The name to use for the output workspace");
}

//----------------------------------------------------------------------------------------------
/** Execute the algorithm.
 */
void LoadILLSANS2::exec() {
  const int NX = 128;
  const int NY = 256;
  const int NZ = 1;
  const int RANK_OUT = 3;
  int i, j, k;
  int data_out[NX][NY][NZ]; /* output buffer */
  for (i = 0; i < NX; i++) {
    for (j = 0; j < NY; j++) {
      for (k = 0; k < NZ; k++)
        data_out[i][j][k] = 0;
    }
  }
  const std::string filename = getPropertyValue("Filename");
  H5File h5file(filename, H5F_ACC_RDONLY);
  DataSet dataset = h5file.openDataSet("/entry0/data/data");
  DataSpace dataspace = dataset.getSpace();
  int rank = dataspace.getSimpleExtentNdims();
  hsize_t dims_out[2];
  int ndims = dataspace.getSimpleExtentDims(dims_out, NULL);
  hsize_t dimsm[3]; /* memory space dimensions */
  dimsm[0] = NX;
  dimsm[1] = NY;
  dimsm[2] = NZ;
  DataSpace memspace(RANK_OUT, dimsm);
  dataset.read(data_out, PredType::NATIVE_INT, memspace, dataspace);
  MatrixWorkspace_sptr ws = createEmptyWorkspace(NX*NY+1, 1);
  std::vector<std::vector<double>> data2D;
  data2D = std::vector<std::vector<double>>(
        NX, std::vector<double>(NY, 0.));
  for (i = 0; i < NX; i++) {
    for (j = 0; j < NY; j++) {
        data2D[i][j] = data_out[i][j][0];
    }
  }
  loadData(data2D, ws);
  runLoadInstrument(ws);
  setProperty("OutputWorkspace", ws);
}

MatrixWorkspace_sptr
LoadILLSANS2::createEmptyWorkspace(const size_t numberOfHistograms,
                                   const size_t numberOfChannels) {
  auto ws = WorkspaceFactory::Instance().create(
      "Workspace2D", numberOfHistograms, numberOfChannels + 1,
      numberOfChannels);
  ws->getAxis(0)->unit() = UnitFactory::Instance().create("Wavelength");
  ws->setYUnitLabel("Counts");
  return ws;
}

void LoadILLSANS2::loadData(const std::vector<std::vector<double>> &data,
                            MatrixWorkspace_sptr ws) {
  const int NX = 128;
  const int NY = 256;
  std::vector<double> binning(2, 0);
  const double wavelength = 6.;
  binning[0] = wavelength - 0.1 * wavelength;
  binning[1] = wavelength + 0.1 * wavelength;
  const HistogramData::BinEdges binEdges(binning);

  PARALLEL_FOR_IF(Kernel::threadSafe(*ws))
  for (size_t i = 0; i < NX; ++i) {
    for (size_t j = 0; j < NY; ++j) {
      ws->setHistogram(i * NY + j, binEdges,
                       HistogramData::Counts({data[i][j]}));
    }
  }
  ws->setHistogram(NY*NX, binEdges,
                   HistogramData::Counts({0.}));
}

void LoadILLSANS2::runLoadInstrument(MatrixWorkspace_sptr ws) {

  IAlgorithm_sptr loadInst = createChildAlgorithm("LoadInstrument");
    loadInst->setPropertyValue("InstrumentName","D22");
  loadInst->setProperty<MatrixWorkspace_sptr>("Workspace", ws);
  loadInst->setProperty("RewriteSpectraMap",
                        Mantid::Kernel::OptionalBool(true));
  loadInst->execute();
}

} // namespace DataHandling
} // namespace Mantid
