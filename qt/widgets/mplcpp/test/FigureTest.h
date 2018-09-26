#ifndef MPLCPP_FIGURETEST_H
#define MPLCPP_FIGURETEST_H

#include "MantidQtWidgets/MplCpp/Figure.h"

#include <cxxtest/TestSuite.h>

using MantidQt::Widgets::MplCpp::Figure;

class FigureTest : public CxxTest::TestSuite {
public:
  static FigureTest *createSuite() { return new FigureTest; }
  static void destroySuite(FigureTest *suite) { delete suite; }

public:
  // ----------------- success tests ---------------------
  void testDefaultFigureHasTightLayout() {
    Figure fig;
    TS_ASSERT_EQUALS(true, fig.pyobj().attr("get_tight_layout")());
  }

  void testConstructFigureWithNoTightLayout() {
    Figure fig{false};
    TS_ASSERT_EQUALS(false, fig.pyobj().attr("get_tight_layout")());
  }
};

#endif // FigureTEST_H
