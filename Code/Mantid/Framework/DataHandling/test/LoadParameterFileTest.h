#ifndef LOADPARAMETERFILETEST_H_
#define LOADPARAMETERFILETEST_H_

#include <cxxtest/TestSuite.h>

#include "MantidDataHandling/LoadParameterFile.h"
#include "MantidDataHandling/LoadInstrument.h"
#include "MantidGeometry/Instrument/FitParameter.h"
#include "MantidAPI/WorkspaceFactory.h"
#include "MantidGeometry/Instrument.h"
#include "MantidDataObjects/Workspace2D.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidKernel/Exception.h"
#include "MantidAPI/FrameworkManager.h"
#include "MantidAPI/Workspace.h"
#include "MantidAPI/Algorithm.h"
#include "MantidGeometry/Instrument/Component.h"
#include "MantidAPI/SpectraDetectorMap.h"
#include <vector>
#include <iostream>

using namespace Mantid::API;
using namespace Mantid::Kernel;
using namespace Mantid::Geometry;
using namespace Mantid::DataHandling;
using namespace Mantid::DataObjects;

class LoadParameterFileTest : public CxxTest::TestSuite
{
public:

  void testExecIDF_for_unit_testing2() // IDF stands for Instrument Definition File
  {
    LoadInstrument loaderIDF2;

    TS_ASSERT_THROWS_NOTHING(loaderIDF2.initialize());

    //create a workspace with some sample data
    wsName = "LoadParameterFileTestIDF2";
    Workspace_sptr ws = WorkspaceFactory::Instance().create("Workspace2D",1,1,1);
    Workspace2D_sptr ws2D = boost::dynamic_pointer_cast<Workspace2D>(ws);

    //put this workspace in the data service
    TS_ASSERT_THROWS_NOTHING(AnalysisDataService::Instance().add(wsName, ws2D));

    // Path to test input file assumes Test directory checked out from SVN
    loaderIDF2.setPropertyValue("Filename", "IDFs_for_UNIT_TESTING/IDF_for_UNIT_TESTING2.xml");
    //inputFile = loaderIDF2.getPropertyValue("Filename");
    loaderIDF2.setPropertyValue("Workspace", wsName);
    TS_ASSERT_THROWS_NOTHING(loaderIDF2.execute());
    TS_ASSERT( loaderIDF2.isExecuted() );

    // load in additional parameters
    LoadParameterFile loaderPF;
    TS_ASSERT_THROWS_NOTHING(loaderPF.initialize());
    loaderPF.setPropertyValue("Filename", "IDFs_for_UNIT_TESTING/IDF_for_UNIT_TESTING2_paramFile.xml");
    loaderPF.setPropertyValue("Workspace", wsName);
    TS_ASSERT_THROWS_NOTHING(loaderPF.execute());
    TS_ASSERT( loaderPF.isExecuted() );


    // Get back the saved workspace
    MatrixWorkspace_sptr output;
    TS_ASSERT_THROWS_NOTHING(output = boost::dynamic_pointer_cast<MatrixWorkspace>(AnalysisDataService::Instance().retrieve(wsName)));

    ParameterMap& paramMap = output->instrumentParameters();
    boost::shared_ptr<Instrument> i = output->getInstrument();
    boost::shared_ptr<IDetector> ptrDet = i->getDetector(1008);
    TS_ASSERT_EQUALS( ptrDet->getID(), 1008);
    TS_ASSERT_EQUALS( ptrDet->getName(), "combined translation6");
    Parameter_sptr param = paramMap.get(&(*ptrDet), "fjols");
    TS_ASSERT_DELTA( param->value<double>(), 20.0, 0.0001);
    param = paramMap.get(&(*ptrDet), "nedtur");
    TS_ASSERT_DELTA( param->value<double>(), 77.0, 0.0001);
    param = paramMap.get(&(*ptrDet), "fjols-test-paramfile");
    TS_ASSERT_DELTA( param->value<double>(), 50.0, 0.0001);

    std::vector<double> dummy = paramMap.getDouble("nickel-holder", "klovn");
    TS_ASSERT_DELTA( dummy[0], 1.0, 0.0001);
    dummy = paramMap.getDouble("nickel-holder", "pos");
    TS_ASSERT_EQUALS (dummy.size(), 0);
    dummy = paramMap.getDouble("nickel-holder", "rot");
    TS_ASSERT_EQUALS (dummy.size(), 0);
    dummy = paramMap.getDouble("nickel-holder", "taabe");
    TS_ASSERT_DELTA (dummy[0], 200.0, 0.0001);
    dummy = paramMap.getDouble("nickel-holder", "mistake");
    TS_ASSERT_EQUALS (dummy.size(), 0);
    dummy = paramMap.getDouble("nickel-holder", "fjols-test-paramfile");
    TS_ASSERT_DELTA (dummy[0], 2000.0, 0.0001);

	AnalysisDataService::Instance().remove(wsName);

  }


private:
  std::string inputFile;
  std::string wsName;

};

#endif /*LOADPARAMETERFILETEST_H_*/
