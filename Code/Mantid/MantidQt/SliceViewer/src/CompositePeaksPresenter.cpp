#include "MantidQtSliceViewer/CompositePeaksPresenter.h"
#include <stdexcept>

namespace MantidQt
{
  namespace SliceViewer
  {
    /**
    Constructor
    */
    CompositePeaksPresenter::CompositePeaksPresenter(ZoomablePeaksView* const zoomablePlottingWidget, PeaksPresenter_sptr defaultPresenter) : m_zoomablePlottingWidget(zoomablePlottingWidget),  
      m_default(defaultPresenter)
    {
      if(m_zoomablePlottingWidget == NULL)
      {
        throw std::runtime_error("Zoomable Plotting Widget is NULL");
      }
    }

    /**
    Destructor
    */
    CompositePeaksPresenter::~CompositePeaksPresenter()
    {
    }

    /**
    Overrriden update method
    */
    void CompositePeaksPresenter::update()
    {
      if(useDefault())
      {
        m_default->update();
        return;
      }
      for(auto it = m_subjects.begin(); it != m_subjects.end(); ++it)
      {
        (*it)->update();
      }
    }

    /**
    Overriden updateWithSlicePoint
    @param point : Slice point to update with 
    */
    void CompositePeaksPresenter::updateWithSlicePoint(const double& point)
    {
      if(useDefault())
      {
        m_default->updateWithSlicePoint(point);
        return;
      }
      for(auto it = m_subjects.begin(); it != m_subjects.end(); ++it)
      {
        (*it)->updateWithSlicePoint(point);
      }
    }

    /**
    Handle dimension display changing.
    */
    bool CompositePeaksPresenter::changeShownDim()
    {
      if(useDefault())
      {
        return m_default->changeShownDim();
      }
      bool result = true;
      for(auto it = m_subjects.begin(); it != m_subjects.end(); ++it)
      {
        result &= (*it)->changeShownDim();
      }
      return result;
    }

    /**
    Determine wheter a given axis label correponds to the free peak axis.
    @return True only if the label is that of the free peak axis.
    */
    bool CompositePeaksPresenter::isLabelOfFreeAxis(const std::string& label) const
    {
      if(useDefault())
      {
        return m_default->isLabelOfFreeAxis(label);
      }
      bool result = true;
      for(auto it = m_subjects.begin(); it != m_subjects.end(); ++it)
      {
        result &= (*it)->isLabelOfFreeAxis(label);
      }
      return result;
    }

    /**
    Clear all peaks
    */
    void CompositePeaksPresenter::clear()
    {
      m_subjects.clear();
      PeakPalette temp;
      m_palette = temp;
    }

    /**
    Add peaks presenter
    @param presenter : Subject peaks presenter
    */
    void CompositePeaksPresenter::addPeaksPresenter(PeaksPresenter_sptr presenter)
    {
      if(this->size() == 10)
      {
        throw std::invalid_argument("Maximum number of PeaksWorkspaces that can be simultaneously displayed is 10.");
      }

      auto result_it = std::find(m_subjects.begin(), m_subjects.end(), presenter);
      if(result_it == m_subjects.end())
      {
        m_subjects.push_back(presenter);
      }
    }

    /**
    @return the number of subjects in the composite
    */
    size_t CompositePeaksPresenter::size() const
    {
      return m_subjects.size();
    }

    /**
    Return a collection of all referenced workspaces on demand.
    */
    SetPeaksWorkspaces CompositePeaksPresenter::presentedWorkspaces() const
    {
      SetPeaksWorkspaces allWorkspaces;
      for(auto it = m_subjects.begin(); it != m_subjects.end(); ++it)
      {
        auto workspacesToAppend = (*it)->presentedWorkspaces();
        allWorkspaces.insert(workspacesToAppend.begin(), workspacesToAppend.end());
      }
      return allWorkspaces;
    }

    /**
    @param ws : Peaks Workspace to look for on sub-presenters.
    @return the identified sub-presenter for the workspace, or a NullPeaksPresenter.
    */
    CompositePeaksPresenter::SubjectContainer::iterator CompositePeaksPresenter::getPresenterIteratorFromWorkspace(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws)
    {
      SubjectContainer::iterator presenterFound = m_subjects.end();
      for(auto presenterIterator = m_subjects.begin(); presenterIterator != m_subjects.end(); ++presenterIterator)
      {
        auto workspacesOfSubject = (*presenterIterator)->presentedWorkspaces();
        SetPeaksWorkspaces::iterator iteratorFound =  workspacesOfSubject.find(ws);
        if(iteratorFound != workspacesOfSubject.end())
        {
          presenterFound = presenterIterator;
          break;
        }
      }
      return presenterFound;
    }

    /**
    @param ws : Peaks Workspace to look for on sub-presenters.
    @return the identified sub-presenter for the workspace, or a NullPeaksPresenter.
    */
    CompositePeaksPresenter::SubjectContainer::const_iterator CompositePeaksPresenter::getPresenterIteratorFromWorkspace(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws) const
    {
      SubjectContainer::const_iterator presenterFound = m_subjects.end();
      for(auto presenterIterator = m_subjects.begin(); presenterIterator != m_subjects.end(); ++presenterIterator)
      {
        auto workspacesOfSubject = (*presenterIterator)->presentedWorkspaces();
        SetPeaksWorkspaces::iterator iteratorFound =  workspacesOfSubject.find(ws);
        if(iteratorFound != workspacesOfSubject.end())
        {
          presenterFound = presenterIterator;
          break;
        }
      }
      return presenterFound;
    }

    /**
    Set the foreground colour of the peaks.
    @ workspace containing the peaks to re-colour
    @ colour to use for re-colouring
    */
    void CompositePeaksPresenter::setForegroundColour(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws, const QColor colour)
    {
      SubjectContainer::iterator iterator = getPresenterIteratorFromWorkspace(ws);
      
      // Update the palette the foreground colour
      const int pos = std::distance(m_subjects.begin(), iterator);
      m_palette.setForegroundColour(pos, colour);

      // Apply the foreground colour
      (*iterator)->setForegroundColour(colour);
    }

    /**
    Set the background colour of the peaks.
    @ workspace containing the peaks to re-colour
    @ colour to use for re-colouring
    */
    void CompositePeaksPresenter::setBackgroundColour(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws,const  QColor colour)
    {
      SubjectContainer::iterator iterator = getPresenterIteratorFromWorkspace(ws);

      // Update the palette background colour.
      const int pos = std::distance(m_subjects.begin(), iterator);
      m_palette.setBackgroundColour(pos, colour);

      // Apply the background colour
      (*iterator)->setBackgroundColour(colour);
    }

    /**
    Getter for the name of the transform.
    @return transform name.
    */
    std::string CompositePeaksPresenter::getTransformName() const
    {
      if(useDefault())
      {
        return m_default->getTransformName();
      }
      return (*m_subjects.begin())->getTransformName();
    }

    /**
    @return a copy of the peaks palette.
    */
    PeakPalette CompositePeaksPresenter::getPalette() const
    {
      return this->m_palette;
    }

    /**
    @param ws: PeakWorkspace to get the colour for.
    @return the foreground colour corresponding to the peaks workspace.
    */
    QColor CompositePeaksPresenter::getForegroundColour(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws) const
    {
      if(useDefault())
      {
        throw std::runtime_error("Foreground colours from palette cannot be fetched until nested presenters are added.");
      }
      SubjectContainer::const_iterator iterator = getPresenterIteratorFromWorkspace(ws);
      const int pos = std::distance(m_subjects.begin(), iterator);
      return m_palette.foregroundIndexToColour(pos);
    }

    /**
    @param ws: PeakWorkspace to get the colour for.
    @return the background colour corresponding to the peaks workspace.
    */
    QColor CompositePeaksPresenter::getBackgroundColour(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws) const
    {
      if(useDefault())
      {
        throw std::runtime_error("Background colours from palette cannot be fetched until nested presenters are added.");
      }
      SubjectContainer::const_iterator iterator = getPresenterIteratorFromWorkspace(ws);
      const int pos = std::distance(m_subjects.begin(), iterator);
      return m_palette.backgroundIndexToColour(pos);
    }

    void CompositePeaksPresenter::setBackgroundRadiusShown(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> ws, const bool shown)
    {
      if(useDefault())
      {
        return m_default->showBackgroundRadius(shown);
      }
      auto iterator = getPresenterIteratorFromWorkspace(ws);
      (*iterator)->showBackgroundRadius(shown);
    }

    void CompositePeaksPresenter::remove(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> peaksWS)
    {
      if(useDefault())
      {
        return;
      }
      auto iterator = getPresenterIteratorFromWorkspace(peaksWS);
      m_subjects.erase(iterator);
    }

    void CompositePeaksPresenter::setShown(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> peaksWS, const bool shown)
    {
      if(useDefault())
      {
        return m_default->setShown(shown);
      }
      auto iterator = getPresenterIteratorFromWorkspace(peaksWS);
      (*iterator)->setShown(shown);
    }

    void CompositePeaksPresenter::zoomToPeak(boost::shared_ptr<const Mantid::API::IPeaksWorkspace> peaksWS, const int peakIndex)
    {
      auto iterator = getPresenterIteratorFromWorkspace(peaksWS);
      auto subjectPresenter = *iterator;
      auto boundingBox = subjectPresenter->getBoundingBox(peakIndex);
      m_zoomablePlottingWidget->zoomToRectangle(boundingBox);
    }
  }
}
