#include "MantidSINQ/PoldiUtilities/PoldiPeakCollection.h"
#include "MantidAPI/TableRow.h"
#include "MantidAPI/WorkspaceFactory.h"
#include "MantidAPI/LogManager.h"
#include "boost/format.hpp"
#include "boost/algorithm/string/join.hpp"

#include "MantidSINQ/PoldiUtilities/MillerIndicesIO.h"
#include "MantidSINQ/PoldiUtilities/UncertainValueIO.h"

namespace Mantid {
namespace Poldi {

using namespace Mantid::API;
using namespace Mantid::DataObjects;

PoldiPeakCollection::PoldiPeakCollection() :
    m_peaks(),
    m_intensityType(Maximum)
{
}

PoldiPeakCollection::PoldiPeakCollection(TableWorkspace_sptr workspace) :
    m_peaks()
{
    if(workspace) {
        constructFromTableWorkspace(workspace);
    }
}

size_t PoldiPeakCollection::peakCount() const
{
    return m_peaks.size();
}

void PoldiPeakCollection::addPeak(PoldiPeak_sptr newPeak)
{
    m_peaks.push_back(newPeak);
}

PoldiPeak_sptr PoldiPeakCollection::peak(size_t index) const
{
    if(index >= m_peaks.size()) {
        throw std::range_error("Peak access index out of range.");
    }

    return m_peaks[index];
}

TableWorkspace_sptr PoldiPeakCollection::asTableWorkspace()
{
    TableWorkspace_sptr peaks = boost::dynamic_pointer_cast<TableWorkspace>(WorkspaceFactory::Instance().createTable());

    prepareTable(peaks);
    peaksToTable(peaks);

    return peaks;
}

PoldiPeakCollection::IntensityType PoldiPeakCollection::intensityType() const
{
    return m_intensityType;
}

void PoldiPeakCollection::prepareTable(TableWorkspace_sptr table)
{
    table->addColumn("str", "HKL");
    table->addColumn("str", "d");
    table->addColumn("str", "Q");
    table->addColumn("str", "Intensity");
    table->addColumn("str", "FWHM (rel.)");

    LogManager_sptr tableLog = table->logs();
    tableLog->addProperty<std::string>("IntensityType", intensityTypeToString(m_intensityType));
}

void PoldiPeakCollection::peaksToTable(TableWorkspace_sptr table)
{
    for(std::vector<PoldiPeak_sptr>::const_iterator peak = m_peaks.begin(); peak != m_peaks.end(); ++peak) {
        TableRow newRow = table->appendRow();
        newRow << MillerIndicesIO::toString((*peak)->hkl())
               << UncertainValueIO::toString((*peak)->d())
               << UncertainValueIO::toString((*peak)->q())
               << UncertainValueIO::toString((*peak)->intensity())
               << UncertainValueIO::toString((*peak)->fwhm(PoldiPeak::Relative));
    }
}

void PoldiPeakCollection::constructFromTableWorkspace(TableWorkspace_sptr tableWorkspace)
{
    if(checkColumns(tableWorkspace)) {
        size_t newPeakCount = tableWorkspace->rowCount();
        m_peaks.resize(newPeakCount);

        m_intensityType = intensityTypeFromString(getIntensityTypeFromTable(tableWorkspace));

        for(size_t i = 0; i < newPeakCount; ++i) {
            TableRow nextRow = tableWorkspace->getRow(i);
            std::string hklString, dString, qString, intensityString, fwhmString;
            nextRow >> hklString >> dString >> qString >> intensityString >> fwhmString;

            PoldiPeak_sptr peak = PoldiPeak::create(MillerIndicesIO::fromString(hklString),
                                                    UncertainValueIO::fromString(dString),
                                                    UncertainValueIO::fromString(intensityString),
                                                    UncertainValueIO::fromString(fwhmString));
            m_peaks[i] = peak;
        }
    }
}

bool PoldiPeakCollection::checkColumns(TableWorkspace_sptr tableWorkspace)
{
    if(tableWorkspace->columnCount() != 5) {
        return false;
    }

    std::vector<std::string> shouldNames;
    shouldNames.push_back("HKL");
    shouldNames.push_back("d");
    shouldNames.push_back("Q");
    shouldNames.push_back("Intensity");
    shouldNames.push_back("FWHM (rel.)");

    std::vector<std::string> columnNames = tableWorkspace->getColumnNames();

    return columnNames == shouldNames;
}

std::string PoldiPeakCollection::getIntensityTypeFromTable(TableWorkspace_sptr tableWorkspace)
{
    LogManager_sptr tableLog = tableWorkspace->logs();

    if(tableLog->hasProperty("IntensityType")) {
        return tableLog->getPropertyValueAsType<std::string>("IntensityType");
    }

    return "";
}

std::string PoldiPeakCollection::intensityTypeToString(PoldiPeakCollection::IntensityType type) const
{
    switch(type) {
    case Maximum:
        return "Maximum";
    case Integral:
        return "Integral";
    }

    throw std::runtime_error("Unkown intensity type can not be processed.");
}

PoldiPeakCollection::IntensityType PoldiPeakCollection::intensityTypeFromString(std::string typeString) const
{
    std::string lowerCaseType(typeString);
    std::transform(lowerCaseType.begin(), lowerCaseType.end(), lowerCaseType.begin(), ::tolower);

    if(lowerCaseType == "integral") {
        return Integral;
    }

    return Maximum;
}

}
}
