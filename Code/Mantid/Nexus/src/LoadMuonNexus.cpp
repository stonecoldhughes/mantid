//----------------------------------------------------------------------
// Includes
//----------------------------------------------------------------------
#include "MantidNexus/LoadMuonNexus.h"
#include "MantidDataObjects/Workspace2D.h"
#include "MantidKernel/UnitFactory.h"
#include "MantidKernel/ConfigService.h"
#include "MantidKernel/ArrayProperty.h"
#include "MantidKernel/FileProperty.h"
#include "MantidGeometry/Instrument/Detector.h"
#include "MantidAPI/Progress.h"
#include "MantidAPI/SpectraDetectorMap.h"
#include "MantidKernel/TimeSeriesProperty.h"

#include "Poco/Path.h"

#include <cmath>
#include <boost/shared_ptr.hpp>
#include "MantidNexus/MuonNexusReader.h"
#include "MantidNexus/NexusClasses.h"


namespace Mantid
{
  namespace NeXus
  {
    // Register the algorithm into the algorithm factory
    DECLARE_ALGORITHM(LoadMuonNexus)

    using namespace Kernel;
    using namespace API;

    /// Empty default constructor
    LoadMuonNexus::LoadMuonNexus() : 
    Algorithm(),
      m_filename(), m_entrynumber(0), m_numberOfSpectra(0), m_numberOfPeriods(0), m_list(false),
      m_interval(false), m_spec_list(), m_spec_min(0), m_spec_max(unSetInt)
    {}

    /// Initialisation method.
    void LoadMuonNexus::init()
    {
      std::vector<std::string> exts;
      exts.push_back("nxs");
      declareProperty(new FileProperty("Filename", "", FileProperty::Load, exts),
        "The name of the Nexus file to load" );      

      declareProperty(new WorkspaceProperty<Workspace>("OutputWorkspace","",Direction::Output),
        "The name of the workspace to be created as the output of the\n"
        "algorithm. For multiperiod files, one workspace will be\n"
        "generated for each period");


      BoundedValidator<int> *mustBePositive = new BoundedValidator<int>();
      mustBePositive->setLower(0);
      declareProperty( "SpectrumMin",0, mustBePositive,
        "Index number of the first spectrum to read, only used if\n"
        "spectrum_max is set and only for single period data\n"
        "(default 0)" );
      declareProperty( "SpectrumMax", unSetInt, mustBePositive->clone(),
        "Index of last spectrum to read, only for single period data\n"
        "(default the last spectrum)");

      declareProperty(new ArrayProperty<int>("SpectrumList"), 
        "Array, or comma separated list, of indexes of spectra to\n"
        "load");
      declareProperty("AutoGroup",false,
        "Determines whether the spectra are automatically grouped\n"
        "together based on the groupings in the NeXus file, only\n"
        "for single period data (default no)");

      declareProperty("EntryNumber", 0, mustBePositive->clone(),
        "The particular entry number to read (default: Load all workspaces and creates a workspace group)");
    }

    /** Executes the algorithm. Reading in the file and creating and populating
    *  the output workspace
    * 
    *  @throw Exception::FileError If the Nexus file cannot be found/opened
    *  @throw std::invalid_argument If the optional properties are set to invalid values
    */
    void LoadMuonNexus::exec()
    {
      // Retrieve the filename from the properties
      m_filename = getPropertyValue("Filename");
      // Retrieve the entry number
      m_entrynumber = getProperty("EntryNumber");

      MuonNexusReader nxload;
      if (nxload.readFromFile(m_filename) != 0)
      {
        g_log.error("Unable to open file " + m_filename);
        throw Exception::FileError("Unable to open File:" , m_filename);  
      }

      // Read in the instrument name from the Nexus file
      m_instrument_name = nxload.getInstrumentName();
      // Read in the number of spectra in the Nexus file
      m_numberOfSpectra = nxload.t_nsp1;
      if(m_entrynumber!=0)
      {
        m_numberOfPeriods=1;
        if(m_entrynumber>nxload.t_nper)
        {
          throw std::invalid_argument("Invalid Entry Number:Enter a valid number");
        }
      }
      else
      {
        // Read the number of periods in this file
        m_numberOfPeriods = nxload.t_nper;
      }
      // Need to extract the user-defined output workspace name
      Property *ws = getProperty("OutputWorkspace");
      std::string localWSName = ws->value();
      // If multiperiod, will need to hold the Instrument, Sample & SpectraDetectorMap for copying
      boost::shared_ptr<IInstrument> instrument;
      boost::shared_ptr<Sample> sample;

      // Call private method to validate the optional parameters, if set
      checkOptionalProperties();

      // Read the number of time channels (i.e. bins) from the Nexus file
      const int channelsPerSpectrum = nxload.t_ntc1;
      // Read in the time bin boundaries 
      const int lengthIn = channelsPerSpectrum + 1;
      float* timeChannels = new float[lengthIn];
      nxload.getTimeChannels(timeChannels, lengthIn);
      // Put the read in array into a vector (inside a shared pointer)
      boost::shared_ptr<MantidVec> timeChannelsVec
        (new MantidVec(timeChannels, timeChannels + lengthIn));

      // Calculate the size of a workspace, given its number of periods & spectra to read
      int total_specs;
      if( m_interval || m_list)
      {
        total_specs = m_spec_list.size();
        if (m_interval)
        {
          total_specs += (m_spec_max-m_spec_min+1);
          m_spec_max += 1;
        }
      }
      else
      {
        total_specs = m_numberOfSpectra;
        // for nexus return all spectra
        m_spec_min = 0; // changed to 0 for NeXus, was 1 for Raw
        m_spec_max = m_numberOfSpectra;  // was +1?
      }

      // Create the 2D workspace for the output
      DataObjects::Workspace2D_sptr localWorkspace = boost::dynamic_pointer_cast<DataObjects::Workspace2D>
        (WorkspaceFactory::Instance().create("Workspace2D",total_specs,lengthIn,lengthIn-1));
      // Set the units on the workspace to TOF & Counts
      localWorkspace->getAxis(0)->unit() = UnitFactory::Instance().create("TOF");
      localWorkspace->setYUnit("Counts");

      WorkspaceGroup_sptr wsGrpSptr=WorkspaceGroup_sptr(new WorkspaceGroup);
      if(m_numberOfPeriods>1)
      {
        if(wsGrpSptr)wsGrpSptr->add(localWSName);
        setProperty("OutputWorkspace",boost::dynamic_pointer_cast<Workspace>(wsGrpSptr));
      }

      API::Progress progress(this,0.,1.,m_numberOfPeriods * total_specs);
      // Loop over the number of periods in the Nexus file, putting each period in a separate workspace
      for (int period = 0; period < m_numberOfPeriods; ++period) {
        if(m_entrynumber!=0)
        {
          period=m_entrynumber-1;
          if(period!=0)
          {
            runLoadInstrument(localWorkspace );
            runLoadMappingTable(localWorkspace );
          }
        }

        if (period == 0)
        {
          // Only run the sub-algorithms once
          runLoadInstrument(localWorkspace );
          runLoadMappingTable(localWorkspace );
          runLoadLog(localWorkspace );
          localWorkspace->populateInstrumentParameters();
        }
        else   // We are working on a higher period of a multiperiod raw file
        {
          localWorkspace =  boost::dynamic_pointer_cast<DataObjects::Workspace2D>
            (WorkspaceFactory::Instance().create(localWorkspace));
          //localWorkspace->newInstrumentParameters(); ???

        }
        std::string outws("");
        if(m_numberOfPeriods>1)
        {
          std::string outputWorkspace = "OutputWorkspace";
          std::stringstream suffix;
          suffix << (period+1);
          outws =outputWorkspace+"_"+suffix.str();
          std::string WSName = localWSName + "_" + suffix.str();
          declareProperty(new WorkspaceProperty<DataObjects::Workspace2D>(outws,WSName,Direction::Output));
          if(wsGrpSptr)wsGrpSptr->add(WSName);
        }

        int counter = 0;
        for (int i = m_spec_min; i < m_spec_max; ++i)
        {
          // Shift the histogram to read if we're not in the first period
          int histToRead = i + period*total_specs;
          loadData(timeChannelsVec,counter,histToRead,nxload,lengthIn-1,localWorkspace ); // added -1 for NeXus
          counter++;
          progress.report();
        }
        // Read in the spectra in the optional list parameter, if set
        if (m_list)
        {
          for(unsigned int i=0; i < m_spec_list.size(); ++i)
          {
            loadData(timeChannelsVec,counter,m_spec_list[i],nxload,lengthIn-1, localWorkspace );
            counter++;
            progress.report();
          }
        }
        // Just a sanity check
        assert(counter == total_specs);

        bool autogroup = getProperty("AutoGroup");

        if (autogroup)
        {

          //Get the groupings
          int max_group = 0;
          // use a map for mapping group number and output workspace index in case 
          // there are group numbers > number of groups
          std::map<int,int> groups;
          m_groupings.resize(nxload.numDetectors);
          bool thereAreZeroes = false;
          for (int i =0; i < nxload.numDetectors; ++i)
          {
            int ig = nxload.detectorGroupings[i];
            if (ig == 0)
            {
              thereAreZeroes = true;
              continue;
            }
            m_groupings[i] = ig;
            if (groups.find(ig) == groups.end())
              groups[ig] = groups.size();
            if (ig > max_group) max_group = ig;
          }

          if (thereAreZeroes)
            for (int i =0; i < nxload.numDetectors; ++i)
            {
              int ig = nxload.detectorGroupings[i];
              if (ig == 0)
              {
                ig = ++max_group;
                m_groupings[i] = ig;
                groups[ig] = groups.size();
              }
            }

          int numHists = localWorkspace->getNumberHistograms();
          int ngroups = int(groups.size()); // number of groups

          // to output groups in ascending order
          {
            int i=0;
            for(std::map<int,int>::iterator it=groups.begin();it!=groups.end();it++,i++)
            {
              it->second = i;
              g_log.information()<<"group "<<it->first<<": ";
              bool first = true;
              int first_i,last_i;
              for(int i=0;i<numHists;i++)
                if (m_groupings[i] == it->first)
                {
                  if (first) 
                  {
                    first = false;
                    g_log.information()<<i;
                    first_i = i;
                  }
                  else
                  {
                    if (first_i >= 0)
                    {
                      if (i > last_i + 1)
                      {
                        g_log.information()<<'-'<<i;
                        first_i = -1;
                      }
                    }
                    else
                    {
                      g_log.information()<<','<<i;
                      first_i = i;
                    }
                  }
                  last_i = i;
                }
                else
                {
                  if (!first && first_i >= 0)
                  {
                    if (last_i > first_i)
                      g_log.information()<<'-'<<last_i;
                    first_i = -1;
                  }
                }
              if (first_i >= 0 && last_i > first_i)
                g_log.information()<<'-'<<last_i;
              g_log.information()<<'\n';
            }
          }

          //Create a workspace with only two spectra for forward and back
          DataObjects::Workspace2D_sptr  groupedWS = boost::dynamic_pointer_cast<DataObjects::Workspace2D>
            (API::WorkspaceFactory::Instance().create(localWorkspace, ngroups, localWorkspace->dataX(0).size(), localWorkspace->blocksize()));

          boost::shared_array<int> spec(new int[numHists]);
          boost::shared_array<int> dets(new int[numHists]);

          //Compile the groups
          for (int i = 0; i < numHists; ++i)
          {    
            int k = groups[ m_groupings[numHists*period + i] ];

            for (int j = 0; j < localWorkspace->blocksize(); ++j)
            {
              groupedWS->dataY(k)[j] = groupedWS->dataY(k)[j] + localWorkspace->dataY(i)[j];

              //Add the errors in quadrature
              groupedWS->dataE(k)[j] 
              = sqrt(pow(groupedWS->dataE(k)[j], 2) + pow(localWorkspace->dataE(i)[j], 2));
            }

            //Copy all the X data
            groupedWS->dataX(k) = localWorkspace->dataX(i);
            spec[i] = k + 1;
            dets[i] = i + 1;
          }

          m_groupings.clear();

          // All two spectra
          for(int k=0;k<ngroups;k++)
          {
            groupedWS->getAxis(1)->spectraNo(k)= k + 1;
          }

          groupedWS->mutableSpectraMap().populate(spec.get(),dets.get(),numHists);

          // Assign the result to the output workspace property
          if(m_numberOfPeriods>1)
            setProperty(outws,groupedWS);
          else
          {
            setProperty("OutputWorkspace",boost::dynamic_pointer_cast<Workspace>(groupedWS));

          }

        }
        else
        {
          // Assign the result to the output workspace property
          if(m_numberOfPeriods>1)
            setProperty(outws,localWorkspace);
          else
          {
            setProperty("OutputWorkspace",boost::dynamic_pointer_cast<Workspace>(localWorkspace));
          }

        }

      } // loop over periods

      // Clean up
      delete[] timeChannels;
    }

    /// Validates the optional 'spectra to read' properties, if they have been set
    void LoadMuonNexus::checkOptionalProperties()
    {
      //read in the settings passed to the algorithm
      m_spec_list = getProperty("SpectrumList");
      m_spec_max = getProperty("SpectrumMax");
      //Are we using a list of spectra or all the spectra in a range?
      m_list = !m_spec_list.empty();
      m_interval = (m_spec_max != unSetInt);
      if ( m_spec_max == unSetInt ) m_spec_max = 0;

      // If a multiperiod dataset, ignore the optional parameters (if set) and print a warning
      //if ( m_numberOfPeriods > 1)
      //{
      //  if ( m_list || m_interval )
      //  {
      //    m_list = false;
      //    m_interval = false;
      //    g_log.warning("Ignoring spectrum properties in this multiperiod dataset");
      //  }
      //}

      // Check validity of spectra list property, if set
      if ( m_list )
      {
        m_list = true;
        const int minlist = *min_element(m_spec_list.begin(),m_spec_list.end());
        const int maxlist = *max_element(m_spec_list.begin(),m_spec_list.end());
        if ( maxlist > m_numberOfSpectra || minlist == 0)
        {
          g_log.error("Invalid list of spectra");
          throw std::invalid_argument("Inconsistent properties defined"); 
        } 
      }

      // Check validity of spectra range, if set
      if ( m_interval )
      {
        m_interval = true;
        m_spec_min = getProperty("SpectrumMin");
        if ( m_spec_max < m_spec_min || m_spec_max > m_numberOfSpectra )
        {
          g_log.error("Invalid Spectrum min/max properties");
          throw std::invalid_argument("Inconsistent properties defined"); 
        }
      }
    }

    /** Load in a single spectrum taken from a NeXus file
    *  @param tcbs     The vector containing the time bin boundaries
    *  @param hist     The workspace index
    *  @param i        The spectrum number
    *  @param nxload   A reference to the MuonNeXusReader object
    *  @param lengthIn The number of elements in a spectrum
    *  @param localWorkspace A pointer to the workspace in which the data will be stored
    */
    void LoadMuonNexus::loadData(const DataObjects::Histogram1D::RCtype::ptr_type& tcbs,int hist, int& i,
      MuonNexusReader& nxload, const int& lengthIn, DataObjects::Workspace2D_sptr localWorkspace)
    {
      // Read in a spectrum
      // Put it into a vector, discarding the 1st entry, which is rubbish
      // But note that the last (overflow) bin is kept
      // For Nexus, not sure if above is the case, hence give all data for now
      MantidVec& Y = localWorkspace->dataY(hist);
      Y.assign(nxload.counts + i * lengthIn, nxload.counts + i * lengthIn + lengthIn);
      // Create and fill another vector for the errors, containing sqrt(count)
      MantidVec& E = localWorkspace->dataE(hist);
      std::transform(Y.begin(), Y.end(), E.begin(), dblSqrt);
      // Populate the workspace. Loop starts from 1, hence i-1
      localWorkspace->setX(hist, tcbs);
      localWorkspace->getAxis(1)->spectraNo(hist)= hist + 1;
    }

    /// Run the sub-algorithm LoadInstrument (or LoadInstrumentFromNexus)
    void LoadMuonNexus::runLoadInstrument(DataObjects::Workspace2D_sptr localWorkspace)
    {
      // Determine the search directory for XML instrument definition files (IDFs)
      std::string directoryName = Kernel::ConfigService::Instance().getString("instrumentDefinition.directory");      
      if ( directoryName.empty() )
      {
        // This is the assumed deployment directory for IDFs, where we need to be relative to the
        // directory of the executable, not the current working directory.
        directoryName = Poco::Path(Mantid::Kernel::ConfigService::Instance().getBaseDir()).resolve("../Instrument").toString();  
      }
      // For Nexus, Instrument name given by MuonNexusReader from Nexus file
      std::string instrumentID = m_instrument_name; //m_filename.substr(stripPath+1,3);  // get the 1st 3 letters of filename part
      // force ID to upper case
      std::transform(instrumentID.begin(), instrumentID.end(), instrumentID.begin(), toupper);
      std::string fullPathIDF = directoryName + "/" + instrumentID + "_Definition.xml";

      IAlgorithm_sptr loadInst = createSubAlgorithm("LoadInstrument");

      // Now execute the sub-algorithm. Catch and log any error, but don't stop.
      bool executionSuccessful(true);
      try
      {
        loadInst->setPropertyValue("Filename", fullPathIDF);
        loadInst->setProperty<MatrixWorkspace_sptr> ("Workspace", localWorkspace);
        loadInst->execute();
      }
      catch( std::invalid_argument&)
      {
        g_log.information("Invalid argument to LoadInstrument sub-algorithm");
        executionSuccessful = false;
      }
      catch (std::runtime_error&)
      {
        g_log.information("Unable to successfully run LoadInstrument sub-algorithm");
        executionSuccessful = false;
      }

      // If loading instrument definition file fails, run LoadInstrumentFromNexus instead
      // This does not work at present as the example files do not hold the necessary data
      // but is a place holder. Hopefully the new version of Nexus Muon files should be more
      // complete.
      if ( ! loadInst->isExecuted() )
      {
        runLoadInstrumentFromNexus(localWorkspace);
      }
    }

    /// Run LoadInstrumentFromNexus as a sub-algorithm (only if loading from instrument definition file fails)
    void LoadMuonNexus::runLoadInstrumentFromNexus(DataObjects::Workspace2D_sptr localWorkspace)
    {
      g_log.information() << "Instrument definition file not found. Attempt to load information about \n"
        << "the instrument from nexus data file.\n";

      IAlgorithm_sptr loadInst = createSubAlgorithm("LoadInstrumentFromNexus");

      // Now execute the sub-algorithm. Catch and log any error, but don't stop.
      bool executionSuccessful(true);
      try
      {
        loadInst->setPropertyValue("Filename", m_filename);
        loadInst->setProperty<MatrixWorkspace_sptr> ("Workspace", localWorkspace);
        loadInst->execute();
      }
      catch( std::invalid_argument&)
      {
        g_log.information("Invalid argument to LoadInstrument sub-algorithm");
        executionSuccessful = false;
      }
      catch (std::runtime_error&)
      {
        g_log.information("Unable to successfully run LoadInstrument sub-algorithm");
        executionSuccessful = false;
      }

      if ( !executionSuccessful ) g_log.error("No instrument definition loaded");      
    }

    /// Run the LoadMappingTable sub-algorithm to fill the SpectraToDetectorMap
    void LoadMuonNexus::runLoadMappingTable(DataObjects::Workspace2D_sptr localWorkspace)
    {
      NXRoot root(m_filename);
      NXInt number = root.openNXInt("run/instrument/detector/number");
      number.load();
      int ndet = number[0]/m_numberOfPeriods;
      boost::shared_array<int> det(new int[ndet]);
      for(int i=0;i<ndet;i++)
        det[i] = i + 1;
      localWorkspace->mutableSpectraMap().populate(det.get(),det.get(),ndet);
    }

    /// Run the LoadLog sub-algorithm
    void LoadMuonNexus::runLoadLog(DataObjects::Workspace2D_sptr localWorkspace)
    {
      IAlgorithm_sptr loadLog = createSubAlgorithm("LoadMuonLog");
      // Pass through the same input filename
      loadLog->setPropertyValue("Filename",m_filename);
      // Set the workspace property to be the same one filled above
      loadLog->setProperty<MatrixWorkspace_sptr>("Workspace",localWorkspace);

      // Now execute the sub-algorithm. Catch and log any error, but don't stop.
      try
      {
        loadLog->execute();
      }
      catch (std::runtime_error&)
      {
        g_log.error("Unable to successfully run LoadLog sub-algorithm");
      }

      if ( ! loadLog->isExecuted() ) g_log.error("Unable to successfully run LoadLog sub-algorithm");


      NXRoot root(m_filename);
      NXChar start_time = root.openNXChar("run/start_time");
      start_time.load();
      NXChar orientation = root.openNXChar("run/instrument/detector/orientation");
      orientation.load();

      if (orientation[0] == 't')
      {
        Kernel::TimeSeriesProperty<double>* p = new Kernel::TimeSeriesProperty<double>("fromNexus");
        p->addValue(start_time(),-90.);
        localWorkspace->mutableSample().addLogData(p);
      }


    }

    double LoadMuonNexus::dblSqrt(double in)
    {
      return sqrt(in);
    }

  } // namespace DataHandling
} // namespace Mantid
