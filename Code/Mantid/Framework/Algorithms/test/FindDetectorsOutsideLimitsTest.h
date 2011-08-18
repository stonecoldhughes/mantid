#ifndef FINDDETECTORSOUTSIDELIMITSTEST_H_
#define FINDDETECTORSOUTSIDELIMITSTEST_H_

#include <cxxtest/TestSuite.h>

#include "MantidAlgorithms/FindDetectorsOutsideLimits.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAPI/WorkspaceFactory.h"
#include "MantidAPI/SpectraDetectorMap.h"
#include "MantidDataObjects/Workspace2D.h"
#include "MantidDataObjects/EventWorkspace.h"
#include "MantidTestHelpers/WorkspaceCreationHelper.h"
#include <Poco/File.h>
#include <fstream>
#include "MantidTestHelpers/ComponentCreationHelper.h"

using namespace Mantid::Algorithms;
using namespace Mantid::API;
using namespace Mantid::DataObjects;
using namespace Mantid::Geometry;
using namespace Mantid::Kernel;

class FindDetectorsOutsideLimitsTest : public CxxTest::TestSuite
{
public:

  FindDetectorsOutsideLimitsTest()
  {
  }

  ~FindDetectorsOutsideLimitsTest()
  {}

  void testInit()
  {
    FindDetectorsOutsideLimits alg;

    TS_ASSERT_THROWS_NOTHING(alg.initialize());
    TS_ASSERT( alg.isInitialized() );
  }

  void testExec()
  {
    const int sizex = 10, sizey = 20;
    // Register the workspace in the data service and initialise it with abitary data
    Workspace2D_sptr work_in =
    //the x values look like this -1, 2, 5, 8, 11, 14, 17, 20, 23, 26
    WorkspaceCreationHelper::Create2DWorkspaceBinned(sizey, sizex, -1, 3.0);

    //yVeryDead is a detector with low counts
    boost::shared_ptr<Mantid::MantidVec> yVeryDead(new Mantid::MantidVec(sizex,0.1));
    //yTooDead gives some counts at the start but has a whole region full of zeros
    double TD[sizex] = {2, 4, 5, 10, 0, 0, 0, 0, 0 , 0}; 
    boost::shared_ptr<Mantid::MantidVec> yTooDead(new Mantid::MantidVec(TD, TD+10));
    //yStrange dies after giving some counts but then comes back
    double S[sizex] = {0.2, 4, 50, 0.001, 0, 0, 0, 0, 1 , 0}; 
    boost::shared_ptr<Mantid::MantidVec> yStrange(new Mantid::MantidVec(S, S+10));
    for (int i=0; i< sizey; i++)
    {
      if (i%3 == 0)
      {//the last column is set arbitrarily to have the same values as the second because the errors shouldn't make any difference
        work_in->setData(i, yTooDead, yTooDead);
      }
      if (i%2 == 0)
      {
        work_in->setData(i, yVeryDead, yVeryDead);
      }
      if (i == 19)
      {
        work_in->setData(i, yStrange, yTooDead);
      }
      work_in->getAxis(1)->spectraNo(i) = i;
      Mantid::Geometry::Detector* det = new Mantid::Geometry::Detector("",i,NULL);
      boost::shared_ptr<Mantid::Geometry::Instrument> instr = boost::dynamic_pointer_cast<Mantid::Geometry::Instrument>(work_in->getBaseInstrument());
      instr->add(det);
      instr->markAsDetector(det);
    }
    int forSpecDetMap[20] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19};
    work_in->replaceSpectraMap(new SpectraDetectorMap(forSpecDetMap,forSpecDetMap,20));

    FindDetectorsOutsideLimits alg;

    AnalysisDataService::Instance().add("testdead_in", work_in);
    alg.initialize();
    alg.setPropertyValue("InputWorkspace","testdead_in");
    alg.setPropertyValue("OutputWorkspace","testdead_out");
    alg.setPropertyValue("LowThreshold","1");
    alg.setPropertyValue("HighThreshold","21.01");
    alg.setPropertyValue("RangeLower", "-1");

    // Testing behavour with Range_lower or Range_upper not set
    TS_ASSERT_THROWS_NOTHING(alg.execute());
    TS_ASSERT( alg.isExecuted() );

    // Get back the output workspace
    MatrixWorkspace_sptr work_out;
    TS_ASSERT_THROWS_NOTHING(work_out = boost::dynamic_pointer_cast<MatrixWorkspace>(AnalysisDataService::Instance().retrieve("testdead_out")));

    const int numFailed = alg.getProperty("NumberOfFailures");
    TS_ASSERT_EQUALS(numFailed, 11);

    const double liveValue(1.0);
    const double maskValue(0.0);
    for (int i=0; i< sizey; i++)
    {
      const double val = work_out->readY(i)[0];
      double valExpected = liveValue;
      // Check masking
      IDetector_sptr det;
      TS_ASSERT_THROWS_NOTHING(det = work_out->getDetector(i));
      bool maskExpected(false);
      // Spectra set up with yVeryDead fail low counts or yStrange fail on high
      if ( i%2 == 0 || i == 19 )
      {
        valExpected = maskValue;
        maskExpected = true;
      }
      if(det)
      {
        TS_ASSERT_EQUALS(det->isMasked(), maskExpected);
      }

      TS_ASSERT_DELTA(val,valExpected,1e-9);
    }

    // Set cut off much of the range and yTooDead will stop failing on high counts
    alg.setPropertyValue("RangeUpper", "4.9");
    alg.initialize();
    TS_ASSERT_THROWS_NOTHING(alg.execute());
    TS_ASSERT( alg.isExecuted() );
    //retrieve the output workspace
    TS_ASSERT_THROWS_NOTHING(work_out = boost::dynamic_pointer_cast<MatrixWorkspace>(AnalysisDataService::Instance().retrieve("testdead_out")));

    const int numFailed2 = alg.getProperty("NumberOfFailures");
    TS_ASSERT_EQUALS(numFailed2, 11); 

    //Check the dead detectors found agrees with what was setup above
    for (int i=0; i< sizey; i++)
    {
      const double val = work_out->readY(i)[0];
      double valExpected = liveValue;
      // Check masking
      IDetector_sptr det;
      TS_ASSERT_THROWS_NOTHING(det = work_out->getDetector(i));
      bool maskExpected(false);
      // Spectra set up with yVeryDead fail low counts or yStrange fail on high
      if ( i%2 == 0 || i == 19 )
      {
        valExpected = maskValue;
        maskExpected = true;
      }
      if(det)
      {
        TS_ASSERT_EQUALS(det->isMasked(), maskExpected);
      }

      TS_ASSERT_DELTA(val,valExpected,1e-9);
    }
    
    AnalysisDataService::Instance().remove("testdead_in");
    AnalysisDataService::Instance().remove("testdead_out");
  }


  void testExec_Event()
  {
    // Make a workspace with 50 pixels, 200 events per pixel.
    EventWorkspace_sptr work_in = WorkspaceCreationHelper::CreateEventWorkspace2();
    Instrument_sptr inst = ComponentCreationHelper::createTestInstrumentCylindrical(10);
    work_in->setInstrument(inst);
    DateAndTime run_start("2010-01-01");
    // Add ten more at #10 so that it fails
    for (int i=0; i<10; i++)
      work_in->getEventList(10).addEventQuickly( TofEvent((i+0.5), run_start+double(i)) );

    AnalysisDataService::Instance().add("testdead_in", work_in);

    FindDetectorsOutsideLimits alg;
    alg.initialize();
    alg.setPropertyValue("InputWorkspace","testdead_in");
    alg.setPropertyValue("OutputWorkspace","testdead_out");
    alg.setPropertyValue("LowThreshold","1");
    alg.setPropertyValue("HighThreshold","201");
    alg.setPropertyValue("RangeLower", "-1");
    alg.setPropertyValue("RangeUpper", "1000");
    alg.execute();
    TS_ASSERT( alg.isExecuted() );

    MatrixWorkspace_sptr work_out;
    TS_ASSERT_THROWS_NOTHING(work_out = boost::dynamic_pointer_cast<MatrixWorkspace>(AnalysisDataService::Instance().retrieve("testdead_out")));

    TS_ASSERT_EQUALS( work_out->dataY(0)[0], 1.0);
    TS_ASSERT_EQUALS( work_out->dataY(9)[0], 1.0);
    TS_ASSERT_EQUALS( work_out->dataY(10)[0], 0.0);
    TS_ASSERT_EQUALS( work_out->dataY(11)[0], 1.0);

    AnalysisDataService::Instance().remove("testdead_in");
    AnalysisDataService::Instance().remove("testdead_out");
  }

};

#endif /*FINDDETECTORSOUTSIDELIMITSTEST_H_*/
