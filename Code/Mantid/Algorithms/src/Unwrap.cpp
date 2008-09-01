//----------------------------------------------------------------------
// Includes
//----------------------------------------------------------------------
#include "MantidAlgorithms/Unwrap.h"
#include "MantidAPI/SpectraDetectorMap.h"
#include "MantidKernel/UnitFactory.h"
#include "MantidKernel/PhysicalConstants.h"

namespace Mantid
{
namespace Algorithms
{

DECLARE_ALGORITHM(Unwrap)

using namespace Kernel;
using namespace API;

// Get a reference to the logger
Logger& Unwrap::g_log = Logger::get("Unwrap");

/// Default constructor
Unwrap::Unwrap()
{}

/// Destructor
Unwrap::~Unwrap()
{}

/// Initialisation method
void Unwrap::init()
{
  declareProperty(new WorkspaceProperty<Workspace>("InputWorkspace","",Direction::Input));
  declareProperty(new WorkspaceProperty<Workspace>("OutputWorkspace","",Direction::Output));

  BoundedValidator<double> *validator = new BoundedValidator<double>;
  validator->setLower(0.01);
  declareProperty("LRef", 0.0, validator);

  // Calculate and set the constant factor for the conversion to wavelength
  const double TOFisinMicroseconds = 1e6;
  const double toAngstroms = 1e10;
  m_conversionConstant = (PhysicalConstants::h * toAngstroms) / (PhysicalConstants::NeutronMass * TOFisinMicroseconds);
}

/** Executes the algorithm
 *  @throw std::runtime_error if the workspace is invalid or a child algorithm fails
 *  @throw Kernel::Exception::InstrumentDefinitionError if detector, source or sample positions cannot be calculated
 *
 */
void Unwrap::exec()
{
  // Get the input workspace
  m_inputWS = getProperty("InputWorkspace");
  // Check the workspace is valid for this algorithm
  this->checkInputWorkspace();

  // Need a new workspace. Will just be used temporarily until the data is rebinned.
  Workspace_sptr tempWS = WorkspaceFactory::Instance().create(m_inputWS);

  // Get the "reference" flightpath (currently passed in as a property)
  m_LRef = getProperty("LRef");
  // Get the min & max frame values
  m_Tmin = m_inputWS->dataX(0).front();
  m_Tmax = m_inputWS->dataX(0).back();
  g_log.debug() << "Frame range in microseconds is: " << m_Tmin << " - " << m_Tmax << std::endl;
  m_XSize = m_inputWS->dataX(0).size();

  // Retrieve the source-sample distance
  const double L1 = this->getPrimaryFlightpath();

  // Get the number of spectra in this workspace
  const int numberOfSpectra = m_inputWS->getNumberHistograms();
  g_log.debug() << "Number of spectra in input workspace: " << numberOfSpectra << std::endl;

  // This will be used later to store the maximum number of bin BOUNDARIES for the rebinning
  unsigned int max_bins = 0;

  // Loop over the histograms (detector spectra)
  for (int i = 0; i < numberOfSpectra; ++i)
  {
    // Flag indicating whether the current detector is a monitor, Set in calculateFlightpath below.
    bool isMonitor;
    const double Ld = this->calculateFlightpath(i, L1, isMonitor);

    // Unwrap the x data. Returns the bin ranges that end up being used
    const std::vector<int> rangeBounds = this->unwrapX(tempWS, i, Ld);
    // Unwrap the y & e data according to the ranges found above
    this->unwrapYandE(tempWS, i, rangeBounds);
    assert( tempWS->dataX(i).size() == tempWS->dataY(i).size()+1 );

    // Get the maximum number of bins (excluding monitors) for the rebinning below
    if ( !isMonitor )
    {
      const unsigned int XLen = tempWS->dataX(i).size();
      if ( XLen > max_bins ) max_bins = XLen;
    }
  } // loop over spectra

  // Calculate the minimum and maximum possible wavelengths for the rebinning
  const double minLambda = (m_conversionConstant * m_Tmin) / m_LRef;
  const double maxLambda = (m_conversionConstant * m_Tmax) / m_LRef;
  // Rebin the data into common wavelength bins
  Workspace_sptr outputWS = this->rebin( tempWS, minLambda, maxLambda, max_bins-1);

  g_log.debug() << "Rebinned workspace has " << outputWS->getNumberHistograms() << " histograms of "
                << outputWS->blocksize() << " bins each" << std::endl;
  // Set the correct X unit on the output workspace
  outputWS->getAxis(0)->unit() = UnitFactory::Instance().create("Wavelength");
  setProperty("OutputWorkspace",outputWS);
}

/** Verifies that the input workspace is compatible with this algorithm
 *  @throw std::runtime_error if the workspace is invalid
 */
void Unwrap::checkInputWorkspace() const
{
  // Check its unit is TOF
  if ( m_inputWS->getAxis(0)->unit()->unitID() != "TOF" )
  {
    g_log.error("Input workspace must have units of TOF");
    throw std::runtime_error("Input workspace must have units of TOF");
  }
  // Check its histogram data
  if ( m_inputWS->dataX(0).size() != m_inputWS->dataY(0).size()+1 )
  {
    g_log.error("Input workspace must contain histogram data");
    throw std::runtime_error("Input workspace must contain histogram data");
  }
  // Workspace data must not be dimensioned
  if ( m_inputWS->isDistribution() )
  {
    g_log.error("Input workspace Y data must be raw counts");
    throw std::runtime_error("Input workspace Y data must be raw counts");
  }
}

/** Gets the primary flightpath (L1)
 *  @return L1
 *  @throw Kernel::Exception::InstrumentDefinitionError if L1 is not available
 */
const double Unwrap::getPrimaryFlightpath() const
{
  // Get a pointer to the instrument contained in the input workspace
  boost::shared_ptr<API::Instrument> instrument = m_inputWS->getInstrument();
  // Get the distance between the source and the sample
  Geometry::ObjComponent* sample = instrument->getSample();
  double L1;
  try
  {
    L1 = instrument->getSource()->getDistance(*sample);
    g_log.debug() << "Source-sample distance (in metres): " << L1 << std::endl;
  }
  catch (Exception::NotFoundError e)
  {
    g_log.error("Unable to calculate source-sample distance");
    throw Exception::InstrumentDefinitionError("Unable to calculate source-sample distance", m_inputWS->getTitle());
  }
  return L1;
}

/** Calculates the total flightpath for the given detector.
 *  This is L1+L2 normally, but is the source-detector distance for a monitor.
 *  @param spectrum  The workspace index
 *  @param L1        The primary flightpath
 *  @param isMonitor Output: true is this detector is a monitor
 *  @return The flightpath (Ld) for the detector linked to spectrum
 *  @throw Kernel::Exception::InstrumentDefinitionError if the detector position can't be obtained
 */
const double Unwrap::calculateFlightpath(const int& spectrum, const double& L1, bool& isMonitor) const
{
  // Get the spectrum number for this histogram
  const int spec = m_inputWS->getAxis(1)->spectraNo(spectrum);
  // Get the detector object for this histogram
  boost::shared_ptr<Geometry::IDetector> det = m_inputWS->getSpectraMap()->getDetector(spec);
  // Get the sample-detector distance for this detector (or source-detector if a monitor)
  // This is the total flightpath
  double Ld;
  try
  {
    isMonitor = det->isMonitor();
    // Get the L2 distance if this detector is not a monitor
    if ( !isMonitor )
    {
      double L2 = det->getPos().distance(m_inputWS->getInstrument()->getSample()->getPos());
      Ld = L1 + L2;
    }
    // If it is a monitor, then the flightpath is the distance to the source
    else
    {
      Ld = det->getPos().distance(m_inputWS->getInstrument()->getSource()->getPos());
    }
  }
  catch (Exception::NotFoundError)
  {
    // Going to be harsh and throw if the detector position is not found.
    g_log.error() << "Detector " << det->getID() << " position not available" << std::endl;
    throw Exception::InstrumentDefinitionError("Detector position not available", m_inputWS->getTitle());
  }

  return Ld;
}

/** Unwraps an X array, converting the units to wavelength along the way.
 *  @param tempWS   A pointer to the temporary workspace in which the results are being stored
 *  @param spectrum The workspace index
 *  @param Ld       The flightpath for the detector related to this spectrum
 *  @return A 3-element vector containing the bins at which the upper and lower ranges start & end
 */
const std::vector<int> Unwrap::unwrapX(const API::Workspace_sptr& tempWS, const int& spectrum, const double& Ld)
{
  // Create and initalise the vector that will store the bin ranges, and will be returned
  // Elements are: 0 - Lower range start, 1 - Lower range end, 2 - Upper range start
  std::vector<int> binRange(3,-1);

  // Calculate cut-off times
  const double T1 = m_Tmax - ( m_Tmin*( 1 - (Ld/m_LRef) ) );
  const double T2 = m_Tmax * (Ld/m_LRef);

  // Create a temporary vector to store the lower range of the unwrapped histograms
  std::vector<double> tempX_L;
  tempX_L.reserve(m_XSize); // Doing this possible gives a small efficiency increase
  // Create a vector for the upper range. Make it a reference to the output histogram to save an assignment later
  std::vector<double> &tempX_U = tempWS->dataX(spectrum);
  tempX_U.clear();
  tempX_U.reserve(m_XSize);

  // Get a reference to the input x data
  const std::vector<double>& xdata = m_inputWS->dataX(spectrum);
  // Loop over histogram, selecting bins in appropriate ranges.
  // At the moment, the data in the bin in which a cut-off sits is excluded.
  for (unsigned int bin = 0; bin < m_XSize; ++bin)
  {
    // This is the time-of-flight value under consideration in the current iteration of the loop
    const double tof = xdata[bin];
    // First deal with bins where m_Tmin < tof < T2
    if ( tof < T2 )
    {
      const double wavelength = (m_conversionConstant * tof) / Ld;
      tempX_L.push_back(wavelength);
      // Record the bins that fall in this range for copying over the data & errors
      if (binRange[0] == -1) binRange[0] = bin;
      binRange[1] = bin;
    }
    // Now do the bins where T1 < tof < m_Tmax
    else if ( tof > T1 )
    {
      const double velocity = Ld / (tof-m_Tmax+m_Tmin);
      const double wavelength = m_conversionConstant / velocity;
      tempX_U.push_back(wavelength);
      // Remove the duplicate boundary bin
      if ( tof == m_Tmax && std::abs(wavelength - tempX_L.front()) < 1.0e-5 ) tempX_U.pop_back();
      // Record the bins that fall in this range for copying over the data & errors
      if (binRange[2] == -1) binRange[2] = bin;
    }
  } // loop over X values

  // Deal with the (rare) case that a detector (e.g. downstream monitor) is at a longer flightpath than m_LRef
  if (Ld > m_LRef)
  {
    std::pair<int,int> binLimits = this->handleFrameOverlapped(xdata, Ld, tempX_L);
    binRange[0] = binLimits.first;
    binRange[1] = binLimits.second;
  }

  // Append first vector to back of second
  tempX_U.insert(tempX_U.end(),tempX_L.begin(),tempX_L.end());

  return binRange;
}

/** Deals with the (rare) case where the flightpath is longer than the reference
 *  Note that in this case both T1 & T2 will be greater than Tmax
 */
std::pair<int,int> Unwrap::handleFrameOverlapped(const std::vector<double>& xdata, const double& Ld, std::vector<double>& tempX)
{
  // Calculate the interval to exclude
  const double Dt = (m_Tmax - m_Tmin) * (1 - (m_LRef/Ld) );
  // This gives us new minimum & maximum tof values
  const double minT = m_Tmin + Dt;
  const double maxT = m_Tmax - Dt;
  int min = 0, max = xdata.size();
  for (unsigned int j = 0; j < m_XSize; ++j)
  {
    const double T = xdata[j];
    if ( T < minT )
    {
      min = j+1;
      tempX.erase(tempX.begin());
    }
    else if ( T > maxT )
    {
      tempX.erase(tempX.end()-max+j, tempX.end());
      max = j-1;
      break;
    }
  }
  return std::make_pair(min,max);
}

/** Unwraps the Y & E vectors of a spectrum according to the ranges found in unwrapX.
 *  @param tempWS      A pointer to the temporary workspace in which the results are being stored
 *  @param spectrum    The workspace index
 *  @param rangeBounds The upper and lower ranges for the unwrapping
 */
void Unwrap::unwrapYandE(const API::Workspace_sptr& tempWS, const int& spectrum, const std::vector<int>& rangeBounds)
{
  // Copy over the relevant ranges of Y & E data
  std::vector<double>& Y = tempWS->dataY(spectrum);
  std::vector<double>& E = tempWS->dataE(spectrum);
  // Get references to the input data
  const std::vector<double>& YIn = m_inputWS->dataY(spectrum);
  const std::vector<double>& EIn = m_inputWS->dataE(spectrum);
  if ( rangeBounds[2] != -1 )
  {
    // Copy in the upper range
    Y.assign( YIn.begin()+rangeBounds[2], YIn.end() );
    E.assign( EIn.begin()+rangeBounds[2], EIn.end() );
  }
  else
  {
    // Y & E are references to existing vector. Assign above clears them, so need to explicitly here
    Y.clear();
    E.clear();
  }
  if ( rangeBounds[0] != -1 && rangeBounds[1] > 0 )
  {
    // Now append the lower range
    std::vector<double>::const_iterator YStart = YIn.begin();
    std::vector<double>::const_iterator EStart = EIn.begin();
    Y.insert( Y.end(), YStart+rangeBounds[0], YStart+rangeBounds[1] );
    E.insert( E.end(), EStart+rangeBounds[0], EStart+rangeBounds[1] );
  }
}

/** Rebins the data into common bins of wavelength.
 *  @param workspace The input workspace to the rebinning
 *  @param min       The lower limit in X for the rebinning
 *  @param max       The upper limit in X for the rebinning
 *  @param numBins   The number of bins into which to rebin
 *  @return A pointer to the workspace containing the rebinned data
 *  @throw std::runtime_error If the Rebin child algorithm fails
 */
API::Workspace_sptr Unwrap::rebin(const API::Workspace_sptr& workspace, const double& min, const double& max, const int& numBins)
{
  // Calculate the width of a bin
  const double step = (max - min)/numBins;

  // Create a Rebin child algorithm
  Algorithm_sptr childAlg = createSubAlgorithm("Rebin");
  childAlg->setPropertyValue("InputWorkspace", "Anonymous");
  childAlg->setProperty<Workspace_sptr>("InputWorkspace", workspace);
  childAlg->setPropertyValue("OutputWorkspace", "Anonymous");

  // Construct the vector that holds the rebin parameters and set the property
  std::vector<double> paramArray;
  paramArray.push_back(min);
  paramArray.push_back(step);
  paramArray.push_back(max);
  childAlg->setProperty<std::vector<double> >("params",paramArray);
  g_log.debug() << "Rebinning unwrapped data into " << numBins << " bins of width " << step
                << " Angstroms, running from " << min << " to " << max << std::endl;

  // Now execute the sub-algorithm. Catch and log any error
  try
  {
    childAlg->execute();
  }
  catch (std::runtime_error& err)
  {
    g_log.error("Unable to successfully run Rebinning sub-algorithm");
    throw;
  }

  if ( ! childAlg->isExecuted() )
  {
    g_log.error("Unable to successfully run Rebinning sub-algorithm");
    throw std::runtime_error("Unable to successfully run Rebinning sub-algorithm");
  }
  else
  {
    return childAlg->getProperty("OutputWorkspace");
  }
}

} // namespace Algorithm
} // namespace Mantid
