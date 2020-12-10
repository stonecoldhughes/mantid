// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#include "MantidQtWidgets/Common/FitScriptGeneratorView.h"
#include "MantidQtWidgets/Common/FitScriptGeneratorDataTable.h"
#include "MantidQtWidgets/Common/IFitScriptGeneratorPresenter.h"

#include "MantidAPI/MatrixWorkspace.h"

#include <algorithm>
#include <iterator>

#include <QMessageBox>

using namespace Mantid::API;
using namespace MantidQt::MantidWidgets;

namespace {

std::vector<WorkspaceIndex>
convertToWorkspaceIndex(std::vector<int> const &indices) {
  std::vector<WorkspaceIndex> workspaceIndices;
  workspaceIndices.reserve(indices.size());
  std::transform(indices.cbegin(), indices.cend(),
                 std::back_inserter(workspaceIndices),
                 [](int index) { return WorkspaceIndex(index); });
  return workspaceIndices;
}

} // namespace

namespace MantidQt {
namespace MantidWidgets {

using ColumnIndex = FitScriptGeneratorDataTable::ColumnIndex;
using FittingType = FitOptionsBrowser::FittingType;
using ViewEvent = IFitScriptGeneratorView::Event;

FitScriptGeneratorView::FitScriptGeneratorView(
    QWidget *parent, QMap<QString, QString> const &fitOptions)
    : IFitScriptGeneratorView(parent), m_presenter(),
      m_dialog(std::make_unique<AddWorkspaceDialog>(this)),
      m_dataTable(std::make_unique<FitScriptGeneratorDataTable>()),
      m_functionTreeView(std::make_unique<FunctionTreeView>(nullptr, true)),
      m_fitOptionsBrowser(std::make_unique<FitOptionsBrowser>(
          nullptr, FittingType::SimultaneousAndSequential)) {
  m_ui.setupUi(this);

  m_ui.fDataTable->layout()->addWidget(m_dataTable.get());
  m_ui.splitter->addWidget(m_functionTreeView.get());
  m_ui.splitter->addWidget(m_fitOptionsBrowser.get());

  setFitBrowserOptions(fitOptions);
  connectUiSignals();
}

FitScriptGeneratorView::~FitScriptGeneratorView() {
  m_dialog.reset();
  m_dataTable.reset();
  m_functionTreeView.reset();
  m_fitOptionsBrowser.reset();
}

void FitScriptGeneratorView::connectUiSignals() {
  connect(m_ui.pbRemove, SIGNAL(clicked()), this, SLOT(onRemoveClicked()));
  connect(m_ui.pbAddWorkspace, SIGNAL(clicked()), this,
          SLOT(onAddWorkspaceClicked()));
  connect(m_dataTable.get(), SIGNAL(cellChanged(int, int)), this,
          SLOT(onCellChanged(int, int)));
  connect(m_dataTable.get(), SIGNAL(itemPressed(QTableWidgetItem *)), this,
          SLOT(onItemPressed()));

  connect(m_functionTreeView.get(),
          SIGNAL(functionRemovedString(const QString &)), this,
          SLOT(onFunctionRemoved(const QString &)));
  connect(m_functionTreeView.get(), SIGNAL(functionAdded(const QString &)),
          this, SLOT(onFunctionAdded(const QString &)));
}

void FitScriptGeneratorView::setFitBrowserOptions(
    QMap<QString, QString> const &fitOptions) {
  for (auto it = fitOptions.constBegin(); it != fitOptions.constEnd(); ++it)
    setFitBrowserOption(it.key(), it.value());
}

void FitScriptGeneratorView::setFitBrowserOption(QString const &name,
                                                 QString const &value) {
  if (name == "FittingType")
    setFittingType(value);
  else
    m_fitOptionsBrowser->setProperty(name, value);
}

void FitScriptGeneratorView::setFittingType(QString const &fitType) {
  if (fitType == "Sequential")
    m_fitOptionsBrowser->setCurrentFittingType(FittingType::Sequential);
  else if (fitType == "Simultaneous")
    m_fitOptionsBrowser->setCurrentFittingType(FittingType::Simultaneous);
  else
    throw std::invalid_argument("Invalid fitting type '" +
                                fitType.toStdString() + "' provided.");
}

void FitScriptGeneratorView::subscribePresenter(
    IFitScriptGeneratorPresenter *presenter) {
  m_presenter = presenter;
}

void FitScriptGeneratorView::onRemoveClicked() {
  m_presenter->notifyPresenter(ViewEvent::RemoveClicked);
}

void FitScriptGeneratorView::onAddWorkspaceClicked() {
  m_presenter->notifyPresenter(ViewEvent::AddClicked);
}

void FitScriptGeneratorView::onCellChanged(int row, int column) {
  UNUSED_ARG(row);
  m_dataTable->formatSelection();

  if (column == ColumnIndex::StartX)
    m_presenter->notifyPresenter(ViewEvent::StartXChanged);
  else if (column == ColumnIndex::EndX)
    m_presenter->notifyPresenter(ViewEvent::EndXChanged);
}

void FitScriptGeneratorView::onItemPressed() {
  m_presenter->notifyPresenter(ViewEvent::SelectionChanged);
}

void FitScriptGeneratorView::onFunctionRemoved(QString const &function) {
  m_presenter->notifyPresenter(ViewEvent::FunctionRemoved,
                               function.toStdString());
}

void FitScriptGeneratorView::onFunctionAdded(QString const &function) {
  m_presenter->notifyPresenter(ViewEvent::FunctionAdded,
                               function.toStdString());
}

std::string FitScriptGeneratorView::workspaceName(FitDomainIndex index) const {
  return m_dataTable->workspaceName(index);
}

WorkspaceIndex
FitScriptGeneratorView::workspaceIndex(FitDomainIndex index) const {
  return m_dataTable->workspaceIndex(index);
}

double FitScriptGeneratorView::startX(FitDomainIndex index) const {
  return m_dataTable->startX(index);
}

double FitScriptGeneratorView::endX(FitDomainIndex index) const {
  return m_dataTable->endX(index);
}

std::vector<FitDomainIndex> FitScriptGeneratorView::allRows() const {
  return m_dataTable->allRows();
}

std::vector<FitDomainIndex> FitScriptGeneratorView::selectedRows() const {
  return m_dataTable->selectedRows();
}

void FitScriptGeneratorView::removeWorkspaceDomain(
    std::string const &workspaceName, WorkspaceIndex workspaceIndex) {
  m_dataTable->removeDomain(workspaceName, workspaceIndex);
}

void FitScriptGeneratorView::addWorkspaceDomain(
    std::string const &workspaceName, WorkspaceIndex workspaceIndex,
    double startX, double endX) {
  m_dataTable->addDomain(QString::fromStdString(workspaceName), workspaceIndex,
                         startX, endX);
}

bool FitScriptGeneratorView::openAddWorkspaceDialog() {
  return m_dialog->exec() == QDialog::Accepted;
}

std::vector<MatrixWorkspace_const_sptr>
FitScriptGeneratorView::getDialogWorkspaces() {
  auto const workspaces = m_dialog->getWorkspaces();
  if (workspaces.empty())
    displayWarning("Failed to add workspace: '" +
                   m_dialog->workspaceName().toStdString() +
                   "' doesn't exist.");
  return workspaces;
}

std::vector<WorkspaceIndex>
FitScriptGeneratorView::getDialogWorkspaceIndices() const {
  return convertToWorkspaceIndex(m_dialog->workspaceIndices());
}

void FitScriptGeneratorView::resetSelection() { m_dataTable->resetSelection(); }

bool FitScriptGeneratorView::isApplyFunctionChangesToAllChecked() const {
  return m_ui.ckApplyFunctionChangesToAll->isChecked();
}

void FitScriptGeneratorView::clearFunction() { m_functionTreeView->clear(); }

void FitScriptGeneratorView::setFunction(
    CompositeFunction_sptr composite) const {
  if (composite->nFunctions() > 1)
    m_functionTreeView->setFunction(composite);
  else if (composite->nFunctions() == 1)
    m_functionTreeView->setFunction(composite->getFunction(0));
  else
    m_functionTreeView->clear();
}

void FitScriptGeneratorView::displayWarning(std::string const &message) {
  QMessageBox::warning(this, "Warning!", QString::fromStdString(message));
}

} // namespace MantidWidgets
} // namespace MantidQt
