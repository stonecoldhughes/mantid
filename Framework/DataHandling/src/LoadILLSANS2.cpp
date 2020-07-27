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
  return "This is a mock loader for grasp simulated D22 hdf files.";
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
  hsize_t dimsm[3]; /* memory space dimensions */
  dimsm[0] = NX;
  dimsm[1] = NY;
  dimsm[2] = NZ;
  DataSpace memspace(RANK_OUT, dimsm);
  dataset.read(data_out, PredType::NATIVE_INT, memspace, dataspace);
  MatrixWorkspace_sptr ws = createEmptyWorkspace(NX * NY + 1, 1);
  std::vector<std::vector<double>> data2D;
  data2D = std::vector<std::vector<double>>(NX, std::vector<double>(NY, 0.));
  for (i = 0; i < NX; i++) {
    for (j = 0; j < NY; j++) {
      data2D[i][j] = data_out[i][j][0];
    }
  }
  double lambda = getScalarEntry(h5file, "/entry0/d22/selector/wavelength");
  loadData(data2D, ws, lambda);
  runLoadInstrument(ws);
  double l2 = getScalarEntry(h5file, "/entry0/d22/detector/det_calc");
  moveDetectorDistance(l2, ws, "detector");
  double timer = getScalarEntry(h5file, "/entry0/duration");
  ws->mutableRun().addProperty<double>("timer", timer, true);
  setPixelSize(ws);
  setProperty("OutputWorkspace", ws);
}

double LoadILLSANS2::getScalarEntry(H5File &h5file, const std::string &entry) {
  DataSet ds = h5file.openDataSet(entry);
  DataSpace dspace = ds.getSpace();
  hsize_t dims[1] = {1};
  DataSpace memspace(1, dims);
  double value[1] = {0};
  ds.read(value, PredType::NATIVE_DOUBLE, memspace, dspace);
  return *value;
}

void LoadILLSANS2::moveDetectorDistance(double distance,
                                        API::MatrixWorkspace_sptr ws,
                                        const std::string &componentName) {

  API::IAlgorithm_sptr mover = createChildAlgorithm("MoveInstrumentComponent");
  V3D pos = getComponentPosition(ws, componentName);
  mover->setProperty<API::MatrixWorkspace_sptr>("Workspace", ws);
  mover->setProperty("ComponentName", componentName);
  mover->setProperty("X", pos.X());
  mover->setProperty("Y", pos.Y());
  mover->setProperty("Z", distance);
  mover->setProperty("RelativePosition", false);
  mover->executeAsChildAlg();
  API::Run &runDetails = ws->mutableRun();
  runDetails.addProperty<double>("L2", distance, true);
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
                            MatrixWorkspace_sptr ws, const double lambda) {
  const int NX = 128;
  const int NY = 256;
  std::vector<double> binning(2, 0);
  binning[0] = lambda - 0.1 * lambda;
  binning[1] = lambda + 0.1 * lambda;
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

V3D LoadILLSANS2::getComponentPosition(API::MatrixWorkspace_sptr ws,
                                       const std::string &componentName) {
  Geometry::Instrument_const_sptr instrument = ws->getInstrument();
  Geometry::IComponent_const_sptr component =
      instrument->getComponentByName(componentName);
  return component->getPos();
}

void LoadILLSANS2::setPixelSize(MatrixWorkspace_sptr ws) {
  const auto instrument = ws->getInstrument();
  const std::string component = "detector";
  auto detector = instrument->getComponentByName(component);
  auto rectangle =
      std::dynamic_pointer_cast<const Geometry::RectangularDetector>(detector);
  if (rectangle) {
    const double dx = rectangle->xstep();
    const double dy = rectangle->ystep();
    API::Run &runDetails = ws->mutableRun();
    runDetails.addProperty<double>("pixel_width", dx);
    runDetails.addProperty<double>("pixel_height", dy);
  } else {
    g_log.debug("No pixel size available");
  }
}

} // namespace DataHandling
} // namespace Mantid
