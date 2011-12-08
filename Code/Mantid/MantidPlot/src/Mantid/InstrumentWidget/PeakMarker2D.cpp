#include "PeakMarker2D.h"

#include <QPainter>
#include <QPainterPath>
#include <QFontMetrics>
#include <QMouseEvent>
#include <QWheelEvent>

#include <iostream>
#include <algorithm>
#include <stdexcept>
#include <cmath>

/// Default size in screen pixels of the marker's symbol
const int PeakMarker2D::g_defaultMarkerSize = 5;

/**
 * Constructor.
 * @param centre :: Centre of the marker. Represents the peak position.
 * @param symbol :: Symbol to draw. One of: Circle, Diamond, or Square
 * @param markerSize :: Optional size of marker's symbol.
 */
PeakMarker2D::PeakMarker2D(const QPointF& centre,Style style):
m_symbol(style.symbol),
m_row(-1)
{
  setColor(style.color);
  if (style.size > 0)
  {
    m_markerSize = style.size;
  }
  else
  {
    m_markerSize = g_defaultMarkerSize;
  }
  m_boundingRect = QRectF(centre - QPointF((qreal)m_markerSize/2,(qreal)m_markerSize/2), 
                          QSizeF((qreal)m_markerSize,(qreal)m_markerSize));
  setScalable(false);
}

bool PeakMarker2D::selectAt(const QPointF& p)const
{
    return contains(p);
}

void PeakMarker2D::drawShape(QPainter& painter) const
{
  // draw the symbol
  switch(m_symbol)
  {
  case Circle: drawCircle(painter); break;
  case Diamond: drawDiamond(painter); break;
  case Square: drawSquare(painter); break;
  default:
    drawCircle(painter);
  }
  // calculate label's area on the screen
  QFontMetrics fm(painter.font());
  QRect r = fm.boundingRect(m_label);
  m_labelRect = QRectF(r);
  m_labelRect.moveTo(m_boundingRect.right() + m_markerSize,m_boundingRect.top() - m_markerSize);
}

void PeakMarker2D::addToPath(QPainterPath& path) const
{
  path.addRect(m_boundingRect);
}

/// Set new marker size to s
void PeakMarker2D::setMarkerSize(const int& s)
{
  if (s > 0)
  {
    m_markerSize = s;
  }
}

/// Draw marker as a circle
void PeakMarker2D::drawCircle(QPainter& painter)const
{
  QPainterPath path;
  path.addEllipse(m_boundingRect);
  painter.fillPath(path,m_color);
}

/// Draw marker as a diamond
void PeakMarker2D::drawDiamond(QPainter& painter)const
{
  QPointF dp = origin();
  QPointF mdp(-dp.x(),-dp.y());
  // draw a diamond as a square rotated by 45 degrees
  painter.save();
  painter.translate(dp);
  painter.rotate(45);
  painter.translate(mdp);
  QPainterPath path;
  path.addRect(m_boundingRect);
  painter.fillPath(path,m_color);
  painter.restore();
}

/// Draw marker as a square
void PeakMarker2D::drawSquare(QPainter& painter)const
{
  QPainterPath path;
  path.addRect(m_boundingRect);
  painter.fillPath(path,m_color);
}

/**
 * Save some peak information.
 */
void PeakMarker2D::setPeak(const Mantid::API::IPeak& peak, int row)
{
  m_h = peak.getH();
  m_k = peak.getK();
  m_l = peak.getL();
  m_label = QString("%1 %2 %3").arg(QString::number(m_h,'g',2),QString::number(m_k,'g',2),QString::number(m_l,'g',2));
  m_detID = peak.getDetectorID();
  m_tof = peak.getTOF();
  m_row = row;
}
