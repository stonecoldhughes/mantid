// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2007 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once
#include "MantidAPI/DllConfig.h"
#include "MantidKernel/DiskBuffer.h"
#include "MantidKernel/System.h"

namespace Mantid {
namespace API {

/** The header describes interface to IO Operations perfomed by the box
 controller
 *  May be replaced by a boost filestream in a future.
 *  It also currently assumes disk buffer usage.
 *  Disk buffer also assumes that actual IO operations performed by the class,
 inhereted from this one are thread-safe
 *
 * @date March 21, 2013

 */

class MANTID_API_DLL IBoxControllerIO : public Kernel::DiskBuffer {
public:
  /** open file for i/o operations
   * @param fileName -- the name of the file to open
   * @param mode     -- the string describing file access mode. if w or W is
   present in the string file is opened in read/write mode.
                        it is opened in read mode otherwise
   * @return false if the file had been already opened. Throws if problems with
   openeing */
  virtual bool openFile(const std::string &fileName,
                        const std::string &mode) = 0;
  /**@return true if file is already opened */
  virtual bool isOpened() const = 0;
  /**@return the full name of the used data file*/
  virtual const std::string &getFileName() const = 0;

  /**Save a float data block in the specified file position */
  virtual void saveBlock(const std::vector<float> & /* DataBlock */,
                         const uint64_t /*blockPosition*/) const = 0;
  /**Save a double data block in the specified file position */
  virtual void saveBlock(const std::vector<double> & /* DataBlock */,
                         const uint64_t /*blockPosition*/) const = 0;
  /** load known size float data block from spefied file position */
  virtual void loadBlock(std::vector<float> & /* Block */,
                         const uint64_t /*blockPosition*/,
                         const size_t /*BlockSize*/) const = 0;
  virtual void loadBlock(std::vector<double> & /* Block */,
                         const uint64_t /*blockPosition*/,
                         const size_t /*BlockSize*/) const = 0;

  /** flush the IO buffers */
  virtual void flushData() const = 0;
  /** Close the file */
  virtual void closeFile() = 0;

  ///  the method which returns the size of data block used in IO operations
  virtual size_t getDataChunk() const = 0;

  /**
   * @brief determine the size (in bytes) storing the state of an event
   *
   * @param blockSize : bytes of the elemental datum (4-float, 8-double)
   * @param typeName : string representation of the event class
   * @param typeVersion : the MDEvent class template has been endowed with
   * additional attributes over time, thus the need for version control
   */
  virtual void setDataType(const size_t blockSize, const std::string &typeName,
                           const uint16_t typeVersion = 2) = 0;
  virtual void getDataType(size_t &blockSize, std::string &typeName) const = 0;
};
} // namespace API
} // namespace Mantid
