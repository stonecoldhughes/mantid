#ifndef MANTID_TESTParCompAssembly__
#define MANTID_TESTParCompAssembly__

#include <cxxtest/TestSuite.h>
#include <cmath>
#include <iostream>
#include <string>
#include "MantidGeometry/CompAssembly.h"
#include "MantidGeometry/ParCompAssembly.h"
#include "MantidGeometry/V3D.h"
#include "MantidGeometry/Quat.h"

using namespace Mantid::Geometry;

class testParCompAssembly : public CxxTest::TestSuite
{
public:
	void testEmptyConstructor()
  {
    CompAssembly q;

    ParameterMap pmap;
    ParCompAssembly pq(&q,pmap);

    TS_ASSERT_EQUALS(pq.nelements(), 0);
    TS_ASSERT_THROWS(pq[0], std::runtime_error);

    TS_ASSERT_EQUALS(pq.getName(), "");
    TS_ASSERT(!pq.getParent());
    TS_ASSERT_EQUALS(pq.getRelativePos(), V3D(0, 0, 0));
    TS_ASSERT_EQUALS(pq.getRelativeRot(), Quat(1, 0, 0, 0));
    //as there is no parent GetPos should equal getRelativePos
    TS_ASSERT_EQUALS(pq.getRelativePos(), pq.getPos());
  }

  void testNameValueConstructor()
  {
    CompAssembly q("Name");

    ParameterMap pmap;
    ParCompAssembly pq(&q,pmap);

    TS_ASSERT_EQUALS(pq.nelements(), 0);
    TS_ASSERT_THROWS(pq[0], std::runtime_error);

    TS_ASSERT_EQUALS(pq.getName(), "Name");
    TS_ASSERT(!pq.getParent());
    TS_ASSERT_EQUALS(pq.getRelativePos(), V3D(0, 0, 0));
    TS_ASSERT_EQUALS(pq.getRelativeRot(), Quat(1, 0, 0, 0));
    //as there is no parent GetPos should equal getRelativePos
    TS_ASSERT_EQUALS(pq.getRelativePos(), pq.getPos());
  }

  void testNameParentValueConstructor()
  {
    CompAssembly* parent = new CompAssembly("Parent");
    //name and parent
    CompAssembly* q = new CompAssembly("Child", parent);

    ParameterMap pmap;
    ParCompAssembly pq(q,pmap);

    TS_ASSERT_EQUALS(pq.getName(), "Child");
    TS_ASSERT_EQUALS(pq.nelements(), 0);
    TS_ASSERT_THROWS(pq[0], std::runtime_error);
    //check the parent
    TS_ASSERT(pq.getParent());
    TS_ASSERT_EQUALS(pq.getParent()->getName(), parent->getName());

    TS_ASSERT_EQUALS(pq.getPos(), V3D(0, 0, 0));
    TS_ASSERT_EQUALS(pq.getRelativeRot(), Quat(1, 0, 0, 0));
    //as the parent is at 0,0,0 GetPos should equal getRelativePos
    TS_ASSERT_EQUALS(pq.getRelativePos(), pq.getPos());
    delete parent;
  }

  void testAdd()
  {
    CompAssembly bank("BankName");
    Component* det1 = new Component("Det1Name");
    Component* det2 = new Component("Det2Name");
    Component* det3 = new Component("Det3Name");
    TS_ASSERT_EQUALS(bank.nelements(), 0);
    TS_ASSERT_THROWS(bank[0], std::runtime_error);
    bank.add(det1);
    bank.add(det2);
    bank.add(det3);

    ParameterMap pmap;
    ParCompAssembly pbank(&bank,pmap);

    TS_ASSERT_EQUALS(pbank.nelements(), 3);
    boost::shared_ptr<IComponent> det1copy;
    TS_ASSERT_THROWS_NOTHING(det1copy = pbank[0]);
    TS_ASSERT_EQUALS(det1->getName(), det1copy->getName());
    //show that they are the same object
    det1->setName("ChangedName");
    TS_ASSERT_EQUALS(det1->getName(), det1copy->getName());

    pmap.addV3D(det2,"pos",V3D(1,1,1));
    boost::shared_ptr<IComponent> det2copy;
    TS_ASSERT_THROWS_NOTHING(det2copy = pbank[1]);
    TS_ASSERT_DIFFERS(det2->getPos(), det2copy->getPos());
  }

  void testGetParent()
  {
    Component parent("Parent", V3D(1, 1, 1), Quat(1, 1, 1, 1));

    CompAssembly q("Child", &parent);

    ParameterMap pmap;
    ParCompAssembly pq(&q,pmap);

    TS_ASSERT(pq.getParent());
    TS_ASSERT_EQUALS(pq.getParent()->getName(), parent.getName());
    TS_ASSERT_EQUALS(pq.getParent()->getPos(), V3D(1, 1, 1));
    TS_ASSERT_EQUALS(pq.getParent()->getRelativeRot(), Quat(1, 1, 1, 1));
  }

  void testType()
  {
    CompAssembly comp;

    ParameterMap pmap;
    ParCompAssembly pcomp(&comp,pmap);

    TS_ASSERT_EQUALS(pcomp.type(), "ParCompAssembly");
  }

};

#endif
