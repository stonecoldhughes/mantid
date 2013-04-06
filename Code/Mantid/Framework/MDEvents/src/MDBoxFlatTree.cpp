#include "MantidKernel/Strings.h"
#include "MantidMDEvents/MDBoxFlatTree.h"
#include "MantidMDEvents/MDEvent.h"
#include "MantidMDEvents/MDLeanEvent.h"
#include "MantidAPI/BoxController.h"
#include "MantidAPI/ExperimentInfo.h"
#include <Poco/File.h>


namespace Mantid
{
  namespace MDEvents
  {
   Kernel::Logger &MDBoxFlatTree::g_log = Kernel::Logger::get("Algorithm");

    MDBoxFlatTree::MDBoxFlatTree():
  m_nDim(-1)
  {     
  }

  /**The method initiates the MDBoxFlatTree class internal structure in the form ready for saving this structure to HDD 
   *
   * @param pws  -- the shared pointer to the MD workspace which is the source of the flat box structure
   * @param fileName -- the name of the file, where this structure should be written. TODO: It is here for the case of file based workspaces
   */
  void MDBoxFlatTree::initFlatStructure(API::IMDEventWorkspace_sptr pws,const std::string &fileName)
  {
    m_bcXMLDescr = pws->getBoxController()->toXMLString();
    m_FileName = fileName;


    m_nDim = int(pws->getNumDims());
    // flatten the box structure
    pws->getBoxes(m_Boxes, 1000, false);

    API::IMDNode::sortObjByID(m_Boxes);

    size_t maxBoxes = m_Boxes.size();
    // Box type (0=None, 1=MDBox, 2=MDGridBox
    m_BoxType.assign(maxBoxes, 0);
    // Recursion depth
    m_Depth.assign(maxBoxes, -1);
    // Start/end indices into the list of events
    m_BoxEventIndex.assign(maxBoxes*2, 0);
    // Min/Max extents in each dimension
    m_Extents.assign(maxBoxes*m_nDim*2, 0);
    // Inverse of the volume of the cell
    m_InverseVolume.assign(maxBoxes, 0);
    // Box cached signal/error squared
    m_BoxSignalErrorsquared.assign(maxBoxes*2, 0);
    // Start/end children IDs
    m_BoxChildren.assign(maxBoxes*2, 0);

    API::IMDNode *Box;
    bool filePositionDefined(true);
    for(size_t i=0;i<maxBoxes;i++)
    {
      Box = m_Boxes[i];
      // currently ID is the number of the box, but it may change in a future. TODO: uint64_t
      size_t id = Box->getID();
      size_t numChildren = Box->getNumChildren();
      if (numChildren > 0) // MDGridBox have childred
      {
        // DEBUG:
        //// Make sure that all children are ordered. TODO: This might not be needed if the IDs are rigorously done
        //size_t lastId = Box->getChild(0)->getId();
        //for (size_t i = 1; i < numChildren; i++)
        //{
        //  if (Box->getChild(i)->getId() != lastId+1)
        //    throw std::runtime_error("Non-sequential child ID encountered!");
        //  lastId = Box->getChild(i)->getId();
        //}

        m_BoxType[id] = 2; 
        m_BoxChildren[id*2] = int(Box->getChild(0)->getID());
        m_BoxChildren[id*2+1] = int(Box->getChild(numChildren-1)->getID());

        // no events but index defined -- TODO -- The proper file has to have consequent indexes for all boxes too. 
        m_BoxEventIndex[id*2]   = 0;
        m_BoxEventIndex[id*2+1] = 0;
      }
      else
      {
        m_BoxType[id] = 1;
        m_BoxChildren[id*2]=0;
        m_BoxChildren[id*2+1]=0;

        //MDBox<MDE,nd> * mdBox = dynamic_cast<MDBox<MDE,nd> *>(Box);
        //if(!mdBox) throw std::runtime_error("found unfamiliar type of box");
        // Store the index

        uint64_t nPoints = Box->getNPoints();
        Kernel::ISaveable *pSaver = Box->getISaveable();
        if(pSaver)
            m_BoxEventIndex[id*2]   = pSaver->getFilePosition();
        else
            filePositionDefined = false;

        m_BoxEventIndex[id*2+1] = nPoints;   
      }

      // Various bits of data about the box
      m_Depth[id] = int(Box->getDepth());
      m_BoxSignalErrorsquared[id*2] = double(Box->getSignal());
      m_BoxSignalErrorsquared[id*2+1] = double(Box->getErrorSquared());
      m_InverseVolume[id] = Box->getInverseVolume();
      for (size_t d=0; d<m_nDim; d++)
      {
        size_t newIndex = id*(m_nDim*2) + d*2;
        m_Extents[newIndex]   = Box->getExtents(d).getMin();
        m_Extents[newIndex+1] = Box->getExtents(d).getMax();

      }
    }
    // file postion have to be calculated afresh
    if(!filePositionDefined)
    {
        uint64_t boxPosition(0);
        for(size_t i=0;i<maxBoxes;i++)
        {
            if(m_BoxType[i]==1)
            {
                m_BoxEventIndex[2*i]=boxPosition;
                boxPosition+=m_BoxEventIndex[2*i+1];
            }
        }
    }

  }
  /*** this function tries to set file positions of the boxes to 
       make data physiclly located close to each otger to be as close as possible on the HDD 
       @param setFileBacked  -- initiate the boxes to be fileBacked. The boxes assumed not to be saved before.
  */
  void MDBoxFlatTree::setBoxesFilePositions(bool setFileBacked)
  {
    // this will preserve file-backed workspace and information in it as we are not loading old box data and not?
    // this would be right for binary axcess but questionable for Nexus --TODO: needs testing
    // Done in INIT--> need check if ID and index in the tree are always the same.
    //Kernel::ISaveable::sortObjByFilePos(m_Boxes);
    // calculate the box positions in the resulting file and save it on place
    uint64_t eventsStart=0;
    for(size_t i=0;i<m_Boxes.size();i++)
    {
      API::IMDNode * mdBox = m_Boxes[i];        
      size_t ID = mdBox->getID();

      // avoid grid boxes;
      if(m_BoxType[ID]==2) continue;

      size_t nEvents = mdBox->getTotalDataSize();
      m_BoxEventIndex[ID*2]   = eventsStart;
      m_BoxEventIndex[ID*2+1] = nEvents;
      if(setFileBacked)
          mdBox->setFileBacked(eventsStart,nEvents,false);

      eventsStart+=nEvents;
    }
  }

  void MDBoxFlatTree::saveBoxStructure(const std::string &fileName)
  {
    m_FileName = fileName;

    auto hFile = std::unique_ptr< ::NeXus::File>(createOrOpenMDWSgroup(fileName,size_t(m_nDim),m_Boxes[0]->getEventType(),false));

    //Save box structure;
    this->saveBoxStructure(hFile.get());
    // close workspace group
    hFile->closeGroup();
    // close file
    hFile->close();  

  }

  void MDBoxFlatTree::saveBoxStructure( ::NeXus::File *hFile)
  {
    size_t maxBoxes = this->getNBoxes();
    if(maxBoxes==0)return;

    std::map<std::string, std::string> groupEntries;
    hFile->getEntries(groupEntries);
 

    bool create(false);
    if(groupEntries.find("box_structure")==groupEntries.end()) //dimesnions dataset exist
          create = true;

    // Start the box data group
    if(create)
    {
      hFile->makeGroup("box_structure", "NXdata",true);
      hFile->putAttr("version", "1.0");
     // Add box controller info to this group
      hFile->putAttr("box_controller_xml", m_bcXMLDescr);

    }
    else
    {
      hFile->openGroup("box_structure", "NXdata");
      // update box controller information
      hFile->putAttr("box_controller_xml", m_bcXMLDescr);
    }


    std::vector<int64_t> exents_dims(2,0);
    exents_dims[0] = (int64_t(maxBoxes));
    exents_dims[1] = (m_nDim*2);
    std::vector<int64_t> exents_chunk(2,0);
    exents_chunk[0] = int64_t(16384);
    exents_chunk[1] = (m_nDim*2);

    std::vector<int64_t> box_2_dims(2,0);
    box_2_dims[0] = int64_t(maxBoxes);
    box_2_dims[1] = (2);
    std::vector<int64_t> box_2_chunk(2,0);
    box_2_chunk[0] = int64_t(16384);
    box_2_chunk[1] = (2);

    if (create)
    {
      // Write it for the first time
      hFile->writeExtendibleData("box_type", m_BoxType);
      hFile->writeExtendibleData("depth", m_Depth);
      hFile->writeExtendibleData("inverse_volume", m_InverseVolume);
      hFile->writeExtendibleData("extents", m_Extents, exents_dims, exents_chunk);
      hFile->writeExtendibleData("box_children", m_BoxChildren, box_2_dims, box_2_chunk);
      hFile->writeExtendibleData("box_signal_errorsquared", m_BoxSignalErrorsquared, box_2_dims, box_2_chunk);
      hFile->writeExtendibleData("box_event_index", m_BoxEventIndex, box_2_dims, box_2_chunk);  
    }
    else
    {
    // Update the extendible data sets
      hFile->writeUpdatedData("box_type", m_BoxType);
      hFile->writeUpdatedData("depth", m_Depth);
      hFile->writeUpdatedData("inverse_volume", m_InverseVolume);
      hFile->writeUpdatedData("extents", m_Extents, exents_dims);
      hFile->writeUpdatedData("box_children", m_BoxChildren, box_2_dims);
      hFile->writeUpdatedData("box_signal_errorsquared", m_BoxSignalErrorsquared, box_2_dims);
      hFile->writeUpdatedData("box_event_index", m_BoxEventIndex, box_2_dims);

    }
    // close the box group.
    hFile->closeGroup();
 

  }

  void MDBoxFlatTree::loadBoxStructure(const std::string &fileName,size_t nDim,const std::string &EventType,bool onlyEventInfo)
  {

    m_FileName = fileName;
    m_nDim = static_cast<unsigned int>(nDim);
    m_eventType = EventType;
 
    // open the file and the MD workspace group.
    auto hFile = std::unique_ptr< ::NeXus::File>(createOrOpenMDWSgroup(fileName,size_t(m_nDim),m_eventType,true));


    //// How many dimensions?
    //std::vector<int32_t> vecDims;
    //hFile->readData("dimensions", vecDims);
    //if (vecDims.empty())
    //    throw std::runtime_error("LoadBoxStructure:: Error loading number of dimensions.");

    //m_nDim = vecDims[0];
    //if (m_nDim<= 0)
    //    throw std::runtime_error("loadBoxStructure:: number of dimensions <= 0.");

      // Now load all the dimension xml
      //this->loadDimensions();

      //if (entryName == "MDEventWorkspace")
      //{
      //  //The type of event
      //  std::string eventType;
      //  file->getAttr("event_type", eventType);

      //  // Use the factory to make the workspace of the right type
      //  IMDEventWorkspace_sptr ws = MDEventFactory::CreateMDWorkspace(m_numDims, eventType);
      //}
    this->loadBoxStructure(hFile.get(),onlyEventInfo);

    // close workspace group
    hFile->closeGroup();
    // close the NeXus file
    hFile->close();
  }
  void MDBoxFlatTree::loadBoxStructure(::NeXus::File *hFile,bool onlyEventInfo)
  {
    // ----------------------------------------- Box Structure ------------------------------
    hFile->openGroup("box_structure", "NXdata");

    if(onlyEventInfo)
    {
      // Load the box controller description
        hFile->getAttr("box_controller_xml", m_bcXMLDescr);
        hFile->readData("box_type", m_BoxType);
        hFile->readData("box_event_index", m_BoxEventIndex);
        return;
    }
    // Load the box controller description
    hFile->getAttr("box_controller_xml", m_bcXMLDescr);


    // Read all the data blocks
    hFile->readData("box_type", m_BoxType);
    size_t numBoxes = m_BoxType.size();
    if (numBoxes == 0) throw std::runtime_error("Zero boxes found. There must have been an error reading or writing the file.");

    hFile->readData("depth", m_Depth);
    hFile->readData("inverse_volume", m_InverseVolume);
    hFile->readData("extents", m_Extents);

    m_nDim = int(m_Extents.size()/(numBoxes*2));
    hFile->readData("box_children", m_BoxChildren);
    hFile->readData("box_signal_errorsquared", m_BoxSignalErrorsquared);
    hFile->readData("box_event_index", m_BoxEventIndex);



    // Check all vector lengths match
    if (m_Depth.size() != numBoxes) throw std::runtime_error("Incompatible size for data: depth.");
    if (m_InverseVolume.size() != numBoxes) throw std::runtime_error("Incompatible size for data: inverse_volume.");
    //if (boxType.size() != numBoxes) throw std::runtime_error("Incompatible size for data: boxType.");
    //if (m_Extents.size() != numBoxes*m_nDim*2) throw std::runtime_error("Incompatible size for data: extents.");
    if (m_BoxChildren.size() != numBoxes*2) throw std::runtime_error("Incompatible size for data: box_children.");
    if (m_BoxEventIndex.size() != numBoxes*2) throw std::runtime_error("Incompatible size for data: box_event_index.");
    if (m_BoxSignalErrorsquared.size() != numBoxes*2) throw std::runtime_error("Incompatible size for data: box_signal_errorsquared.");

    hFile->closeGroup();

  }

  /// Save each NEW ExperimentInfo to a spot in the file
  void MDBoxFlatTree::saveExperimentInfos(::NeXus::File * const file, API::IMDEventWorkspace_const_sptr ws)
  {

      std::map<std::string,std::string> entries;
      file->getEntries(entries);
      for (uint16_t i=0; i < ws->getNumExperimentInfo(); i++)
      {
          API::ExperimentInfo_const_sptr ei = ws->getExperimentInfo(i);
          std::string groupName = "experiment" + Kernel::Strings::toString(i);
          if (entries.find(groupName) == entries.end())
          {
              // Can't overwrite entries. Just add the new ones
              file->makeGroup(groupName, "NXgroup", true);
              file->putAttr("version", 1);
              ei->saveExperimentInfoNexus(file);
              file->closeGroup();

              // Warning for high detector IDs.
              // The routine in MDEvent::saveVectorToNexusSlab() converts detector IDs to single-precision floats
              // Floats only have 24 bits of int precision = 16777216 as the max, precise detector ID
              detid_t min = 0;
              detid_t max = 0;
              try
              {
                  ei->getInstrument()->getMinMaxDetectorIDs(min, max);
              }
              catch (std::runtime_error &)
              { /* Ignore error. Min/max will be 0 */ }

              if (max > 16777216)
              {
                  g_log.warning() << "This instrument (" << ei->getInstrument()->getName() <<
                      ") has detector IDs that are higher than can be saved in the .NXS file as single-precision floats." << std::endl;
                  g_log.warning() << "Detector IDs above 16777216 will not be precise. Please contact the developers." << std::endl;
              }
          }
      }

  }

  //----------------------------------------------------------------------------------------------
  /** Load the ExperimentInfo blocks, if any, in the NXS file
  *
  * @param ws :: MDEventWorkspace/MDHisto to load
  */
  void MDBoxFlatTree::loadExperimentInfos(::NeXus::File * const file,boost::shared_ptr<Mantid::API::MultipleExperimentInfos> ws)
  {
      // First, find how many experimentX blocks there are
      std::map<std::string,std::string> entries;
      file->getEntries(entries);
      std::map<std::string,std::string>::iterator it = entries.begin();
      std::vector<bool> hasExperimentBlock;
      uint16_t numExperimentInfo = 0;
      for (; it != entries.end(); ++it)
      {
          std::string name = it->first;
          if (boost::starts_with(name, "experiment"))
          {
              try
              {
                  uint16_t num = boost::lexical_cast<uint16_t>(name.substr(10, name.size()-10));
                  if (num+1 > numExperimentInfo)
                  {
                      numExperimentInfo = uint16_t(num+uint16_t(1));
                      hasExperimentBlock.resize(numExperimentInfo, false);
                      hasExperimentBlock[num] = true;
                  }
              }
              catch (boost::bad_lexical_cast &)
              { /* ignore */ }
          }
      }

      // Now go through in order, loading and adding
      for (uint16_t i=0; i < numExperimentInfo; i++)
      {
          std::string groupName = "experiment" + Kernel::Strings::toString(i);
          if (!numExperimentInfo)
          {
              g_log.warning() << "NXS file is missing a ExperimentInfo block " << groupName << ". Workspace will be missing ExperimentInfo." << std::endl;
              break;
          }
          file->openGroup(groupName, "NXgroup");
          API::ExperimentInfo_sptr ei(new API::ExperimentInfo);
          std::string parameterStr;
          try
          {
              // Get the sample, logs, instrument
              ei->loadExperimentInfoNexus(file, parameterStr);
              // Now do the parameter map
              ei->readParameterMap(parameterStr);
              // And set it in the workspace.
              ws->addExperimentInfo(ei);
          }
          catch (std::exception & e)
          {
              g_log.information("Error loading section '" + groupName + "' of nxs file.");
              g_log.information(e.what());
          }
          file->closeGroup();
      }

  }



  template<typename MDE,size_t nd>
  uint64_t MDBoxFlatTree::restoreBoxTree(std::vector<API::IMDNode *>&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly)
  {

    size_t numBoxes = this->getNBoxes();
    Boxes.assign(numBoxes, NULL);

    uint64_t totalNumEvents(0);
    m_nDim = int(bc->getNDims());
    if(m_nDim<=0||m_nDim>11 )throw std::runtime_error("Workspace dimesnions are not defined properly");

    for (size_t i=0; i<numBoxes; i++)
    {

      size_t box_type = m_BoxType[i];
      if (box_type == 0)continue;

      MDBoxBase<MDE,nd> * ibox = NULL;
      MDBox<MDE,nd> * box;

      // Extents of the box, as a vector
      std::vector<Mantid::Geometry::MDDimensionExtents<coord_t> > extentsVector(m_nDim);
      for (size_t d=0; d<size_t(m_nDim); d++)
        extentsVector[d].setExtents(static_cast<double>(m_Extents[i*m_nDim*2 + d*2]),static_cast<double>(m_Extents[i*m_nDim*2 + d*2 + 1]));

      // retrieve initial and file location and the numner of the events which belong to this box stored on the HDD
      uint64_t indexStart = m_BoxEventIndex[i*2];
      uint64_t numEvents  = m_BoxEventIndex[i*2+1];

         totalNumEvents+=numEvents;
      if (box_type == 1)
      {
        // --- Make a MDBox -----
        if(BoxStructureOnly)
        {
            box = new MDBox<MDE,nd>(bc.get(), m_Depth[i], extentsVector);
        }
        else // !BoxStructureOnly)
        {

          if(FileBackEnd)
          {
            box = new MDBox<MDE,nd>(bc.get(), m_Depth[i], extentsVector,-1);
            // Mark the box as file backed and indicate that the box was saved
            box->setFileBacked(indexStart,numEvents,true);
          }
          else
          {
            box = new MDBox<MDE,nd>(bc.get(), m_Depth[i], extentsVector,int64_t(numEvents));
          }           
        } // ifBoxStructureOnly
        ibox = box;
      }
      else if (box_type == 2)
      {
        // --- Make a MDGridBox -----
        ibox = new MDGridBox<MDE,nd>(bc.get(), m_Depth[i], extentsVector);
      }
      else
        continue;
      // Force correct ID
      ibox->setID(i);
      // calculate volume from extents;
      ibox->calcVolume();
      if(std::fabs(ibox->getInverseVolume()-m_InverseVolume[i])>1.e-4)
      {
          g_log.debug()<<" Accuracy warning for box N "<<i<<" as stored inverse volume is : "<<m_InverseVolume[i]<<" and calculated from extents: "<<ibox->getInverseVolume()<<std::endl;
          ibox->setInverseVolume(coord_t(m_InverseVolume[i]));
      }

      // Set the cached values
      ibox->setSignal(m_BoxSignalErrorsquared[i*2]);
      ibox->setErrorSquared(m_BoxSignalErrorsquared[i*2+1]);

      // Save the box at its index in the vector.
      Boxes[i] = ibox;

    } // end Box loop

    // Go again, giving the children to the parents
    for (size_t i=0; i<numBoxes; i++)
    {
      if (m_BoxType[i] == 2)
      {
        size_t indexStart = m_BoxChildren[i*2];
        size_t indexEnd   = m_BoxChildren[i*2+1] + 1;
        Boxes[i]->setChildren(Boxes, indexStart, indexEnd);
      }
    }
    bc->setMaxId(numBoxes);
    return totalNumEvents;
      return 0;
  }
  /** The function to create a NeXus MD workspace group with specified events type and number of dimensions or opens the existing group, 
      which corresponds to the input parameters.
   *@param fileName -- the name of the file to create  or open WS group 
   *@param nDims     -- number of workspace dimensions;
   *@param WSEventType -- the string describing event type
   *@param readOnly    -- true if the file is opened for read-only access

   *@return   NeXus pointer to properly opened NeXus data file and group.
   *
   *@throws if group or its component do not exist and the file is opened read-only or if the existing file parameters are not equal to the 
              input parameters.
  */
  ::NeXus::File * MDBoxFlatTree::createOrOpenMDWSgroup(const std::string &fileName,size_t nDims, const std::string &WSEventType, bool readOnly)
  {
        Poco::File oldFile(fileName);
        bool fileExists = oldFile.exists();
        if (!fileExists && readOnly)
            throw Kernel::Exception::FileError("Attempt to open non-existing file in read-only mode",fileName);

       NXaccess access(NXACC_RDWR);
       if(readOnly)
           access =NXACC_READ;

       std::unique_ptr< ::NeXus::File> hFile;
        try
        {
           if(fileExists)
              hFile = std::unique_ptr< ::NeXus::File> ( new ::NeXus::File(fileName, access));
          else
              hFile = std::unique_ptr< ::NeXus::File> (new ::NeXus::File(fileName, NXACC_CREATE5));
        }
        catch(...)
        {
          throw Kernel::Exception::FileError("Can not open NeXus file",fileName);
        }

      std::map<std::string, std::string> groupEntries;

        hFile->getEntries(groupEntries);
        if(groupEntries.find("MDEventWorkspace")!=groupEntries.end()) // WS group exist
        {
        // Open and check ws group -------------------------------------------------------------------------------->>>
            hFile->openGroup("MDEventWorkspace", "NXentry");

            std::string eventType;
            if(hFile->hasAttr("event_type"))
            {
                hFile->getAttr("event_type",eventType);

                if(eventType != WSEventType)
                      throw Kernel::Exception::FileError("Trying to open MDWorkspace nexus file with the the events: "+eventType+
                      "\n different from workspace type: "  +WSEventType,fileName);
            }
            else // it is possible that woerkspace group has been created by somebody else and there are no this kind of attribute attached to it. 
            {
                if(readOnly) 
                    throw Kernel::Exception::FileError("The NXdata group: MDEventWorkspace opened in read-only mode but \n"
                                                       " does not have necessary attribute describing the event type used",fileName);
                 hFile->putAttr("event_type", WSEventType);
            }
            // check dimesions dataset
            bool dimDatasetExist(false);
            hFile->getEntries(groupEntries);
            if(groupEntries.find("dimensions")!=groupEntries.end()) //dimesnions dataset exist
                dimDatasetExist = true;

              if(dimDatasetExist)
              {
                int32_t nFileDims;
                hFile->readData<int32_t>("dimensions",nFileDims);
                if(nFileDims != static_cast<int32_t>(nDims))
                        throw Kernel::Exception::FileError("The NXdata group: MDEventWorkspace initiated for different number of dimensions then requested ",
                        fileName);
              }
              else
              {
                 auto nFileDim = static_cast<int32_t>(nDims);
              // Write out  # of dimensions
                 hFile->writeData("dimensions", nFileDim);
              }
        // END Open and check ws group --------------------------------------------------------------------------------<<<<
        }
        else 
        {
        // create new WS group      ------------------------------------------------------------------------------->>>>>
          if(readOnly) 
              throw Kernel::Exception::FileError("The NXdata group: MDEventWorkspace does not exist in the read-only file",fileName);

           try
           {
                hFile->makeGroup("MDEventWorkspace", "NXentry", true);
                hFile->putAttr("event_type",WSEventType);

                auto nDim = int32_t(nDims);
              // Write out  # of dimensions
                 hFile->writeData("dimensions", nDim);
           }catch(...){
                throw Kernel::Exception::FileError("Can not create new NXdata group: MDEventWorkspace",fileName);
           }
          //END create new WS group      -------------------------------------------------------------------------------<<<
        }
        return hFile.release();
  }


  // TODO: Get rid of this --> create  the box generator and move all below into MDBoxFactory!
  
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<1>, 1>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<2>, 2>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<3>, 3>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<4>, 4>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<5>, 5>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<6>, 6>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<7>, 7>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<8>, 8>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDLeanEvent<9>, 9>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);

  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<1>, 1>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<2>, 2>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<3>, 3>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<4>, 4>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<5>, 5>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<6>, 6>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<7>, 7>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<8>, 8>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);
  template DLLExport uint64_t MDBoxFlatTree::restoreBoxTree<MDEvent<9>, 9>(std::vector<API::IMDNode * >&Boxes,API::BoxController_sptr bc, bool FileBackEnd,bool BoxStructureOnly);

  }
}
