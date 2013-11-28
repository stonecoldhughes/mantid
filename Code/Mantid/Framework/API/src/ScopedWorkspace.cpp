#include "MantidAPI/ScopedWorkspace.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAPI/WorkspaceGroup.h"

namespace Mantid
{
namespace API
{
  
  const size_t ScopedWorkspace::NAME_LENGTH = 16;

  //----------------------------------------------------------------------------------------------
  /** 
   * Constructor
   */
  ScopedWorkspace::ScopedWorkspace()
  {
    // Randomize 
    srand( static_cast<unsigned int>( time(0) ) );

    m_name = generateUniqueName();
  }
    
  //----------------------------------------------------------------------------------------------
  /** 
   * Destructor
   */
  ScopedWorkspace::~ScopedWorkspace()
  {
    AnalysisDataServiceImpl& ads = AnalysisDataService::Instance();

    // When destructed, remove workspace from the ADS if was added and still exists
    if ( ads.doesExist(m_name) )
    {
      if ( ads.retrieveWS<WorkspaceGroup>(m_name) )
      {
        // If is a group, need to remove all the members as well
        ads.deepRemoveGroup(m_name);
      }
      else
      {
        ads.remove(m_name);
      }
    }
  }

  /**
   * Generates a tricky name which is unique within ADS.  
   */
  std::string ScopedWorkspace::generateUniqueName()
  {
    std::string newName;

    do 
    { 
      // __ makes it hidden in the MantidPlot
      newName = "__ScopedWorkspace_" + randomString(NAME_LENGTH);
    } 
    while( AnalysisDataService::Instance().doesExist(newName) );

    return newName;
  }

  /**
   * Generates random alpha-numeric string.
   * @param len :: Length of the string
   * @return Random string of the given length
   */
  std::string ScopedWorkspace::randomString(size_t len)
  {
    static const std::string alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";

    std::string result;
    result.reserve(len);

    while(result.size() != len) 
    {
      size_t randPos = ( (rand() % (alphabet.size() - 1)));
      result.push_back(alphabet[randPos]);
    }

    return result;
  }

} // namespace API
} // namespace Mantid
