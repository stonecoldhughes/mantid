#include "MantidQtCustomInterfaces/ReflMainViewPresenter.h"
#include "MantidAPI/ITableWorkspace.h"
#include "MantidQtCustomInterfaces/ReflMainView.h"
#include "MantidAPI/AlgorithmManager.h"
using namespace Mantid::API;

namespace MantidQt
{
  namespace CustomInterfaces
  {

    const int ReflMainViewPresenter::COL_RUNS(0);
    const int ReflMainViewPresenter::COL_ANGLE(1);
    const int ReflMainViewPresenter::COL_TRANSMISSION(2);
    const int ReflMainViewPresenter::COL_QMIN(3);
    const int ReflMainViewPresenter::COL_QMAX(4);
    const int ReflMainViewPresenter::COL_DQQ(5);
    const int ReflMainViewPresenter::COL_SCALE(6);
    const int ReflMainViewPresenter::COL_GROUP(7);

    ReflMainViewPresenter::ReflMainViewPresenter(ReflMainView* view): m_view(view)
    {
    }

    ReflMainViewPresenter::ReflMainViewPresenter(ITableWorkspace_sptr model, ReflMainView* view): m_model(model), m_view(view)
    {
    }

    ReflMainViewPresenter::~ReflMainViewPresenter()
    {
    }

    /**
    Process selected rows
    */
    void ReflMainViewPresenter::process()
    {
      if(m_model->rowCount() == 0)
      {
        m_view->giveUserWarning("Cannot process an empty Table","Warning");
        return;
      }

      std::vector<size_t> rows = m_view->getSelectedRowIndexes();
      if(rows.size() == 0)
      {
        //Does the user want to abort?
        if(!m_view->askUserYesNo("This will process all rows in the table. Continue?","Process all rows?"))
          return;

        //They want to process all rows, so populate rows with every index in the model
        for(size_t idx = 0; idx < m_model->rowCount(); ++idx)
          rows.push_back(idx);
      }

      for(auto it = rows.begin(); it != rows.end(); ++it)
      {
        try
        {
          validateRow(*it);
        }
        catch(std::exception& ex)
        {
          const std::string rowNo = Mantid::Kernel::Strings::toString<size_t>(*it + 1);
          m_view->giveUserCritical("Error found in row " + rowNo + ":\n" + ex.what(), "Error");
          return;
        }
      }

      m_view->setProgressRange(0, (int)rows.size());
      int progress = 0;
      for(auto it = rows.begin(); it != rows.end(); ++it)
      {
        try
        {
          processRow(*it);
          m_view->setProgress(++progress);
        }
        catch(std::exception& ex)
        {
          const std::string rowNo = Mantid::Kernel::Strings::toString<size_t>(*it + 1);
          const std::string message = "Error encountered while processing row " + rowNo + ": \n";
          m_view->giveUserCritical(message + ex.what(), "Error");
          return;
        }
      }
    }

    /**
    Validate a row
    @param rowNo : The row in the model to validate
    @throws std::invalid_argument if the row fails validation
    */
    void ReflMainViewPresenter::validateRow(size_t rowNo) const
    {
      const std::string   runStr = m_model->String(rowNo, COL_RUNS);
      const std::string   dqqStr = m_model->String(rowNo, COL_DQQ);
      const std::string thetaStr = m_model->String(rowNo, COL_ANGLE);
      const std::string  qMinStr = m_model->String(rowNo, COL_QMIN);
      const std::string  qMaxStr = m_model->String(rowNo, COL_QMAX);

      if(runStr.empty())
        throw std::invalid_argument("Run column may not be empty.");

      if(dqqStr.empty() && thetaStr.empty())
        throw std::invalid_argument("Theta and dQ/Q columns may not BOTH be empty.");

      if(qMinStr.empty())
        throw std::invalid_argument("Qmin column may not be empty.");

      if(qMaxStr.empty())
        throw std::invalid_argument("Qmax column may not be empty.");
    }

    /**
    Fetches a run from disk or the AnalysisDataService
    @param run : The name of the run
    @throws std::runtime_error if the run cannot be found
    @returns a shared pointer to the workspace
    */
    Workspace_sptr ReflMainViewPresenter::fetchRun(const std::string& run, const std::string& instrument = "")
    {
      //First, let's see if the run given is the name of a workspace in the ADS
      if(AnalysisDataService::Instance().doesExist(run))
        return AnalysisDataService::Instance().retrieveWS<Workspace>(run);

      const std::string filename = instrument + run;

      //We'll just have to load it ourselves
      IAlgorithm_sptr algLoadRun = AlgorithmManager::Instance().create("Load");
      algLoadRun->initialize();
      algLoadRun->setChild(true);
      algLoadRun->setProperty("Filename", filename);
      algLoadRun->setProperty("OutputWorkspace", filename + "_TOF");
      algLoadRun->execute();

      if(!algLoadRun->isExecuted())
        throw std::runtime_error("Could not open " + filename);

      return algLoadRun->getProperty("OutputWorkspace");
    }

    /**
    Process a row
    @param rowNo : The row in the model to process
    @throws std::runtime_error if processing fails
    */
    void ReflMainViewPresenter::processRow(size_t rowNo)
    {
      const std::string         run = m_model->String(rowNo, COL_RUNS);
      const std::string    transStr = m_model->String(rowNo, COL_TRANSMISSION);
      const std::string transWSName = makeTransWSName(transStr);

      double   dqq = 0;
      double theta = 0;
      double  qmin = 0;
      double  qmax = 0;

      const bool   dqqGiven = !m_model->String(rowNo, COL_DQQ  ).empty();
      const bool thetaGiven = !m_model->String(rowNo, COL_ANGLE).empty();
      const bool  qminGiven = !m_model->String(rowNo, COL_QMIN ).empty();
      const bool  qmaxGiven = !m_model->String(rowNo, COL_QMAX ).empty();

      if(dqqGiven)
        Mantid::Kernel::Strings::convert<double>(m_model->String(rowNo, COL_DQQ), dqq);

      if(thetaGiven)
        Mantid::Kernel::Strings::convert<double>(m_model->String(rowNo, COL_ANGLE), theta);

      if(qminGiven)
        Mantid::Kernel::Strings::convert<double>(m_model->String(rowNo, COL_QMIN), qmin);

      if(qmaxGiven)
        Mantid::Kernel::Strings::convert<double>(m_model->String(rowNo, COL_QMAX), qmax);

      Workspace_sptr runWS = fetchRun(run, m_view->getProcessInstrument());

      //If the transmission workspace already exists, re-use it.
      MatrixWorkspace_sptr transWS;
      if(AnalysisDataService::Instance().doesExist(transWSName))
        transWS = AnalysisDataService::Instance().retrieveWS<MatrixWorkspace>(transWSName);
      else
        transWS = makeTransWS(transStr);

      IAlgorithm_sptr algReflOne = AlgorithmManager::Instance().create("ReflectometryReductionOneAuto");
      algReflOne->initialize();
      algReflOne->setChild(true);
      algReflOne->setProperty("InputWorkspace", runWS);
      algReflOne->setProperty("FirstTransmissionRun", transWS);
      algReflOne->setProperty("OutputWorkspace", run + "_IvsQ");
      algReflOne->setProperty("OutputWorkspaceWaveLength", run + "_IvsLam");
      algReflOne->setProperty("ThetaIn", theta);
      algReflOne->execute();

      if(!algReflOne->isExecuted())
        throw std::runtime_error("Failed to run ReflectometryReductionOneAuto.");

      MatrixWorkspace_sptr runWSQ = algReflOne->getProperty("OutputWorkspace");
      MatrixWorkspace_sptr runWSLam = algReflOne->getProperty("OutputWorkspaceWaveLength");

      std::vector<double> built_params;
      built_params.push_back(qmin);
      built_params.push_back(-dqq);
      built_params.push_back(qmax);

      IAlgorithm_sptr algRebinQ = AlgorithmManager::Instance().create("Rebin");
      algRebinQ->initialize();
      algRebinQ->setChild(true);
      algRebinQ->setProperty("InputWorkspace", runWSQ);
      algRebinQ->setProperty("Params", built_params);
      algRebinQ->setProperty("OutputWorkspace", run + "_IvsQ_binned");
      algRebinQ->execute();

      IAlgorithm_sptr algRebinLam = AlgorithmManager::Instance().create("Rebin");
      algRebinLam->initialize();
      algRebinLam->setChild(true);
      algRebinLam->setProperty("InputWorkspace", runWSLam);
      algRebinLam->setProperty("Params", built_params);
      algRebinLam->setProperty("OutputWorkspace", run + "_IvsLam_binned");
      algRebinLam->execute();

      MatrixWorkspace_sptr runWSQBin = algRebinQ->getProperty("OutputWorkspace");
      MatrixWorkspace_sptr runWSLamBin = algRebinLam->getProperty("OutputWorkspace");

      //Finally, place the resulting workspaces into the ADS.
      AnalysisDataService::Instance().addOrReplace(run + "_TOF", runWS);

      AnalysisDataService::Instance().addOrReplace(run + "_IvsQ", runWSQ);
      AnalysisDataService::Instance().addOrReplace(run + "_IvsLam", runWSLam);

      AnalysisDataService::Instance().addOrReplace(run + "_IvsQ_binned", runWSQBin);
      AnalysisDataService::Instance().addOrReplace(run + "_IvsLam_binned", runWSLamBin);

      AnalysisDataService::Instance().addOrReplace(transWSName, transWS);
    }

    /**
    Converts a transmission workspace input string into its ADS name
    @param transString : the comma separated transmission run numbers to use
    @returns the ADS name the transmission run should be stored as
    */
    std::string ReflMainViewPresenter::makeTransWSName(const std::string& transString) const
    {
      std::vector<std::string> transVec;
      boost::split(transVec, transString, boost::is_any_of(","));
      return "TRANS_" + transVec[0] + (transVec.size() > 1 ? "_" + transVec[1] : "");
    }

    /**
    Create a transmission workspace
    @param transString : the numbers of the transmission runs to use
    */
    MatrixWorkspace_sptr ReflMainViewPresenter::makeTransWS(const std::string& transString)
    {
      const size_t maxTransWS = 2;

      std::vector<std::string> transVec;
      std::vector<Workspace_sptr> transWSVec;

      //Take the first two run numbers
      boost::split(transVec, transString, boost::is_any_of(","));
      if(transVec.size() > maxTransWS)
        transVec.resize(maxTransWS);

      if(transVec.size() == 0)
        throw std::runtime_error("Failed to parse the transmission run list.");

      for(auto it = transVec.begin(); it != transVec.end(); ++it)
        transWSVec.push_back(fetchRun(*it, m_view->getProcessInstrument()));

      //We have the runs, so we can create a TransWS
      IAlgorithm_sptr algCreateTrans = AlgorithmManager::Instance().create("CreateTransmissionWorkspaceAuto");
      algCreateTrans->initialize();
      algCreateTrans->setChild(true);
      algCreateTrans->setProperty("FirstTransmissionRun", boost::dynamic_pointer_cast<MatrixWorkspace>(transWSVec[0]));
      if(transWSVec.size() > 1)
        algCreateTrans->setProperty("SecondTransmissionRun", boost::dynamic_pointer_cast<MatrixWorkspace>(transWSVec[1]));

      algCreateTrans->setProperty("OutputWorkspace", makeTransWSName(transString));

      if(!algCreateTrans->isInitialized())
        throw std::runtime_error("Could not initialize CreateTransmissionWorkspaceAuto");

      algCreateTrans->execute();

      if(!algCreateTrans->isExecuted())
        throw std::runtime_error("CreateTransmissionWorkspaceAuto failed to execute");

      return algCreateTrans->getProperty("OutputWorkspace");
    }

    /**
    Add row(s) to the model
    */
    void ReflMainViewPresenter::addRow()
    {
      std::vector<size_t> rows = m_view->getSelectedRowIndexes();
      if (rows.size() == 0)
      {
        m_model->appendRow();
      }
      else
      {
        //as selections have to be contigous, then all that needs to be done is add
        //a number of rows at the highest index equal to the size of the returned vector
        std::sort (rows.begin(), rows.end());
        for (size_t idx = rows.size(); 0 < idx; --idx)
        {
          m_model->insertRow(rows.at(0));
        }
      }

      m_view->showTable(m_model);
    }

    /**
    Delete row(s) from the model
    */
    void ReflMainViewPresenter::deleteRow()
    {
      std::vector<size_t> rows = m_view->getSelectedRowIndexes();
      std::sort(rows.begin(), rows.end());
      for(size_t idx = rows.size(); 0 < idx; --idx)
        m_model->removeRow(rows.at(0));

      m_view->showTable(m_model);
    }

    /**
    Used by the view to tell the presenter something has changed
    */
    void ReflMainViewPresenter::notify(int flag)
    {
      switch(flag)
      {
      case ReflMainView::SaveAsFlag:    saveAs();     break;
      case ReflMainView::SaveFlag:      save();       break;
      case ReflMainView::AddRowFlag:    addRow();     break;
      case ReflMainView::DeleteRowFlag: deleteRow();  break;
      case ReflMainView::ProcessFlag:   process();    break;

      case ReflMainView::NoFlags:       return;
      }
      //Not having a 'default' case is deliberate. gcc issues a warning if there's a flag we aren't handling.
    }

    /**
    Load the model into the table
    */
    void ReflMainViewPresenter::load()
    {
      m_view->showTable(m_model);
    }
  }
}
