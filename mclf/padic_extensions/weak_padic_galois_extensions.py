r"""
Weak p-adic Galois extensions
=============================

Let `K` be a `p`-adic number field. For our project we need to be able to
compute with Galois extensions `L/K` of large ramification degree.
For instance, we need to be able to compute the breaks of the ramification
filtration of the Galois group of `L/K`, as well as the corresponding
subfields.

At the moment, computations with large Galois extensions of `p`-adic fields are
still problematic. In particular, it seems difficult to obtain results which are
provably correct. For this reason we do not work which `p`-adic numbers at all.
Instead, we use our own class ``FakepAdicCompletion``, in which a `p`-adic number
field is approximated by a pair `(K_0, v_K)`, where `K_0` is a suitable number field
and `v_K` is a `p`-adic valuation on `K_0` such that `K` is the completion
of `K_0` at `v_K`.

Let `L/K` be a finite field extension. We say that `L/K` is a **weak Galois
extension** if the induced extension  `L^{nr}/K^{nr}` is Galois. Given a
polynomial `f` in `K[x]`, we say that `L/K` is a **weak splitting field** for `f`
if `f` splits over `L^{nr}`.

Given a weak Galois extension `L/K`, we have canonical isomorphisms between the
following groups:

- the Galois group of `L^{nr}/K^{nr}`,
- the inertia subgroup of the Galois closure of `L/K`,

Moreover, this isomorphism respects the filtrations by higher ramification
groups.

If `L/K` is totally ramified then the degree of `L/K` is equal to the degree
of `L^{nr}/K^{nr}`, which is equal to the order of the inertia subgroup of the
Galois closure of `L/K`. Therefore, our approach allows us to fully
understand the inertia group of a Galois extension of `p`-adic fields, while
keeping the degree of the field extensions with which one works as small as
possible.

Our method can also be used to work with approximations of the subfields
of a `p`-adic Galois extension corresponding to the higher ramification
subgroups.

For `u\geq 0` we let `L^{sh,u}` denote the subfield of `L^{sh}/K^{sh}`
corresponding to the `u`th filtration step of the Galois group of
`L^{sh}/K^{sh}`. Then the completion of `L^{sh,u}` agrees with the maximal
unramified extension of the subextension `\hat{L}^u` of the Galois closure
`\hat{L}/\hat{K}` corresponding to the `u`th ramification step. Moreover,
there exists a finite extensions `L^u/K`, together with an extension `v_{L^u}`
of `v_K` to `L^u` such that

- the strict henselization of `(L^u, v_{L^u})` is isomorphic to `L^{sh,u}`,
- the completion of `(L^u, v_{L^u})` agrees with `\hat{L}^u`, up to a finite
  unramified extension.

Note that `L^u` will in general not be a subfield of `L` (and not even of the
Galois closure of `L/K`).


In this module we define a class ``WeakPadicGaloisExtension``, which realizes an
approximation of a `p`-adic Galois extension, up to unramified extensions.


AUTHORS:

- Stefan Wewers (2017-08-06): initial version


EXAMPLES:

This example is from the "Database of Local Fields":  ::

    sage: K = QQ
    sage: v_3 = pAdicValuation(K, 3)
    sage: R.<x> = K[]
    sage: f = x^6+6*x^4+6*x^3+18
    sage: L = WeakPadicGaloisExtension(v_3, f)
    sage: L.upper_jumps()
    [0, 1/2]


TO DO:



"""

#*****************************************************************************
#       Copyright (C) 2017 Stefan Wewers <stefan.wewers@uni-ulm.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************


from sage.structure.sage_object import SageObject
from sage.rings.number_field.number_field import NumberField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.polynomial.polynomial_element import Polynomial
from sage.rings.integer_ring import IntegerRing
from sage.rings.rational_field import RationalField
from sage.rings.finite_rings.integer_mod import mod
from sage.misc.cachefunc import cached_method
from sage.rings.infinity import Infinity
from sage.functions.generalized import sgn
from sage.functions.other import ceil
from sage.misc.prandom import randint
from sage.geometry.newton_polygon import NewtonPolygon
from sage.misc.misc_c import prod
from sage.arith.misc import lcm
from mac_lane import *
from mclf.padic_extensions.fake_padic_completions import FakepAdicCompletion
from mclf.padic_extensions.fake_padic_extensions import FakepAdicExtension

ZZ = IntegerRing()
QQ = RationalField()


class WeakPadicGaloisExtension(FakepAdicExtension):
    r"""
    Return the weak p-adic splitting field of a polynomial.

    INPUT:

    - ``K`` -- a `p`-adic number field
    - ``F`` -- a polynomial over the number field underlying `K`, or a list of
      such polynomials
    - ``minimal_ramification`` -- a positive integer (default: ``1``)

    OUTPUT: the extension `L/K`, where `L` is a weak splitting field of ``F``
    whose ramification index over `K` is a multiple of ``minimal_ramification``.

    NOTE:

    For the time being, ``F`` has to be defined oover `\mathbb{Q}`,
    and ``minimal ramification`` has to be prime to `p`.

    """
    def __init__(self, K, F, minimal_ramification=ZZ(1)):

        # if F is a polynomial, replace it by the list of its irreducible factors
        # if isinstance(F, Polynomial):
        #     F = [f for f, m in F.factor()]
        assert K.is_Qp(), "for the moment, K has to be Q_p"
        assert not K.p().divides(minimal_ramification), "minimal_ramification has to be prime to p"
        if not isinstance(F, Polynomial):
            if F == []:
                F = PolynomialRing(K.number_field(),'x')(1)
            else:
                F = prod(F)
        self._base_field = K
        L = K.weak_splitting_field(F)
        e = ZZ(L.absolute_ramification_degree()/K.absolute_ramification_degree())
        if not minimal_ramification.divides(e):
                        # enlarge the absolute ramification index of vL
                        # such that minimal_ramification divides e(vL/vK):
            m = ZZ(eL*minimal_ramification/e.gcd(minimal_ramification))
            L = L.ramified_extension(m)
            # if m was not prime to p, L/K may not be weak Galois anymore
        else:
            m = ZZ(1)
        self._extension_field = L
        self._ramification_degree = e*m
        self._degree = ZZ(L.absolute_degree()/K.absolute_degree())
        self._inertia_degree = ZZ(L.absolute_inertia_degree()/K.absolute_inertia_degree())
        assert self._degree == self._ramification_degree * self._inertia_degree


    def __repr__(self):
        return "%s as weak Galois extension of %s"%(self._extension_field, self._base_field)


    def ramification_filtration(self, upper_numbering=False):
        r"""
        Return the list of ramification jumps.

        INPUT:

        - ``upper_numbering`` -- a boolean (default: ``False``)

        OUTPUT: an ordered list of pairs `(u, m_u)`, where `u` is a jump in the
        filtration of higher ramification groups and `m_u` is the order of the
        corresponding subgroup. The ordering is by increasing jumps.

        If ``upper_numbering`` is ``False``, then the filtration is defined as
        follows. Let `L/K` be a Galois extension of `p`-adic number fields, with
        Galois group `G`. Let `\pi` be a prime element of `L`, and let `v_L`
        denote the normalized valuation on `L` (such that `v_L(\pi)=1`). For
        `u\geq 0`, the ramification subgroup `G_u` consists of all element
        `\sigma` of the inertia subgroup `I` of `G` such that

        .. MATH::

             v_L(\sigma(\pi) - \pi) \geq i + 1.

        In particular, `I=G_0`. An integer `u\geq 0` is called a "jump" if
        `G_{u+1}` is strictly contained in `G_u`. Note that this is equivalent
        to the condition that there exists an element `\sigma\in G` such that

        .. MATH::

            v_L(\sigma(\pi) - \pi) = u + 1.

        It follows that the ramification filtration can easily be read off from
        the Newton polygon (with respect to `v_L`) of the polynomial

        .. MATH::

            G := P(x + \pi)/x,

        where `P` is a minimal polynomial of `\pi` over `K`.  The polynomial
        `G` is called the *ramification polynomial* of the Galois extension `L/K`.

        """

        if upper_numbering:
            if hasattr(self, "_upper_jumps"):
                return self._upper_jumps
            else:
                self._compute_upper_jumps()
                return self._upper_jumps
        else:
            if hasattr(self, "_lower_jumps"):
                return self._lower_jumps
            else:
                self._compute_lower_jumps()
                return self._lower_jumps


    def lower_jumps(self):
        r"""
        Return the upper jumps of the ramification filtration of this extension.

        """
        return [u for u, m in self.ramification_filtration()]


    def upper_jumps(self):
        r"""
        Return the lower jumps of the ramification filtration of this extension.

        """
        return [u for u, m in self.ramification_filtration(upper_numbering=True)]


    def _compute_lower_jumps(self):
        """
        This method computes the lower jumps and stores them
        as ``_lower_jumps``.

        """
        if self.ramification_degree() == 1:
            self._lower_jumps = []
        else:
            NP = self.ramification_polygon()
            f = self.inertia_degree()
            # this is the Newton polygon of the ramification
            # polygon G
            jumps = []
            for v1, v2 in NP.sides():
                u = (v1[1]-v2[1])/(v2[0]-v1[0]) - 1  # jump = -slope - 1
                if u == 0:                # G does not distinguish Gamma and Gamma_0
                    m = self.ramification_degree()
                else:
                    m = v2[0] + 1
                jumps.append((u, m))
            jumps.reverse()               # increasing order for jumps
            if len(jumps) >= 2 and jumps[0][1] == jumps[1][1]:
                jumps = jumps[1:]     # u=0 is not a jump
            self._lower_jumps = jumps


    def _compute_upper_jumps(self):
        """
        This method computes the upper jumps and stores them
        as ``_upper_jumps``.

        """
        if self.lower_jumps() == []:
            self._upper_jumps = []
        else:
            jumps = self.ramification_filtration()
            m = [m_i for m_i, g_i in jumps]
            g = [g_i for m_i, g_i in jumps]
            e = self.ramification_degree()
            u = [m[0]*g[0]/e]
            for i in range(1, len(jumps)):
                u.append(u[i-1]+(m[i]-m[i-1])*g[i]/e)
            self._upper_jumps = [(u[i], g[i]) for i in range(len(jumps))]


    def ramification_polynomial(self):
        r"""
        Return the ramification polynomial of this extension.

        The *ramification polynomial* of a weak Galois extension `L/K`
        of `p`-adic number fields is the polynomial

        .. MATH::

            G := P(x+\pi)/x

        where `\pi` is a prime element of `L` which generates the extension
        `L/K` and `P` is the minimal polynomial of `\pi` over `K^{nr}`, the
        maximal unramified subextension of `L/K`.

        NOTE:

        For the time being, we have to assume that `K=\mathbb{Q}_p`. In this
        case we can choose for `\pi` the canonical generator of the absolute
        number field `L_0` underlying `L`.

        """
        pass


    def ramification_polygon(self):
        r"""
        Return the ramification polygon of this extension.

        The *ramification polygon* of a weak Galois extension `L/K`
        of `p`-adic number fields is the Newton polygon of the
        ramification polynomial, i.e. the polynomial

        .. MATH::

            G := P(x+\pi)/x

        where `\pi` is a prime element of `L` which generates the extension
        `L/K` and `P` is the minimal polynomial of `\pi` over `K^{nr}`, the
        maximal unramified subextension of .

        The (strictly negative) slopes of the ramification polygon (with respect
        to the valuation `v_L` on `L`, normalized such that `v_L(\pi_L)=1`)
        correspond to the jumps in the filtration of higher ramification groups,
        and the abscissae of the vertices of the corresponding vertices are equal
        to the order of the ramification subgroups that occur in the filtration.

        NOTE:

        - For the time being, we have to assume that `K=\mathbb{Q}_p`. In this
          case we can choose for `\pi` the canonical generator of the absolute
          number field `L_0` underlying `L`.
        - At the moment the algorithm has an heuristic element and does not
          guarantee that the result is correct.

        """
        if not hasattr(self, "_ramification_polygon"):
            assert self.base_field().is_Qp(), "K has to be equal to Q_p"
            P = L.polynomial()
            v_Knr = unramified_extension(self.p(), self.inertia_degree())
            Knr = v_Knr.domain()
            P = P.change_ring(Knr)
            V = v_Knr.mac_lane_approximants(P, assume_squarefree=True, require_incomparability=True, require_maximal_degree=True)
            print "V = ", V
            v = V[0]
            for i in range(10):
                if v.mu() < Infinity:
                    v = v.mac_lane_step(P)[0]
                else:
                    break
            # careful: so far I have no guarantee that the approximation P1 is good enough
            P1 = v.phi()
            assert P1.degree() == self.ramification_degree()
            v = LimitValuation(v, P1)
            v = v.scale(self.ramification_degree())
            S = PolynomialRing(P.parent(), 'T')
            G = P1(P1.parent().gen()+S.gen()).shift(-1)
            self._ramification_polygon = NewtonPolygon([(i, v(G[i])) for i in range(G.degree()+1)])
        return self._ramification_polygon


    def ramification_subfields(self):
        r"""
        Return the ramification subfields of this weak Galois extension.

        The set of all subfields is returned as dictionary, in which the
        keys are the lower jumps and the values are the corresponding subfields,
        given as extension of the base field.

        """
        if hasattr(self, "_ramification_subfields"):
            return self._ramification_subfields
        # do something

        self._ramification_subfields = subfields
        return subfields


    def ramification_subfield(self, u):
        r"""
        Return the ramification subfield corresponding to a given lower jump.

        Here a nonnegative integer `u \geq 0` is called a *lower jump* for the
        weak `p`-adic Galois extension `L/K`  if `u`is a jump in the filtration
        `(G_u)_{u\geq 0}` of the Galois group `G = Gal(L^{nr}/K^{nr})` of the
        induced extension `L^{nr}/K^{nr}`. This is equivalent to the following
        condition: there exists an element `g\in G`, such that

        .. MATH::

                v_L(g(\pi_L)-\pi_L) = u + 1.

        Here `v_L` is the valuation of the extension field `L` and `\pi_L`
        is a prime element of `L`. We normalize `v_L` such that `v_L(\pi_L)=1`.

        """
        ramification_subfields = self.ramification_subfields()
        assert u in ramification_subfields.keys(), "u is not a lower jump"
        return ramification_subfield[u]


    # this function should be obsolete

    def compute_ramification_filtration(self, subfields=False):
        r"""
        Compute the ramification filtration of this weak Galois extension.

        This methods computes the ramification filtration of this weak Galois
        extension `L/K`, with respect to the lower numbering. If ``subfields``
        is ``True``, the subextensions of `L/K` corresponding to the jumps of
        the filtration are also computed.

        """

        if self._ram_degree == ZZ(1):
            jumps = []
        else:
            vK1 = padic_unramified_extension(vK, self._inertia_degree)
            K1 = vK1.domain()
            P = piL.minpoly().change_ring(K1)
            P1 = padic_irreducible_factor(vK1, P)
            assert P1.degree() == self._ram_degree
            R = P1.parent()
            v1 = vK1.mac_lane_approximants(P1)[0]
            v1 = LimitValuation(v1, P1)
            v1 = v1.scale(1/v1(v1.uniformizer()))
            assert v1(P1) == Infinity
            S = PolynomialRing(R, 'T')
            G = P1(S(R.gen()) + S.gen()).shift(-1)
            NP = NewtonPolygon([(i, v1(G[i])) for i in range(G.degree()+1)])
            jumps = []
            for v1, v2 in NP.sides():
                u = (v1[1]-v2[1])/(v2[0]-v1[0]) - 1  # jump = -slope - 1
                m = v2[0] + 1
                if u == 0:                # G does not distinguish Gamma and Gamma_0
                    m = self._ram_degree
                jumps.append((u, m))
            jumps.reverse()               # increasing order for jumps
            if len(jumps) >= 2 and jumps[0][1] == jumps[1][1]:
                jumps = jumps[1:]     # u=0 is not a jump
        self._lower_jumps = jumps

        # compute ramificaton jumps, upper numbering:

        if jumps == []:
            self._upper_jumps = []
        else:
            m = [m_i for m_i, g_i in jumps]
            g = [g_i for m_i, g_i in jumps]
            e = self._ram_degree
            u = [m[0]*g[0]/e]
            for i in range(1, len(jumps)):
                u.append(u[i-1]+(m[i]-m[i-1])*g[i]/e)
            self._upper_jumps = [(u[i], g[i]) for i in range(len(jumps))]


#-----------------------------------------------------------------------------

def unramified_extension(p, n):
    r"""
    Return the unramified extension of Q_p of given degree.

    INPUT:

    - ``p`` -- a prime number
    - ``n`` -- a positive integer

    OUTPUT:

    A pair `(K_0, v_K)`, where `K_0` is an absolute number field of degree `f`
    and `v_K` is a `p`-adic valuation on `K_0`, such that the completion of
    `K_0` at `v_K` is the unique unramified extension of `\mathbb{Q}_p` of
    degree `n`.

    """
    v_p = pAdicValuation(QQ, p)
    if n == 1:
        return v_p

    g = GF(p**n).polynomial().change_ring(ZZ)
    K0 = NumberField(g, 'zeta')
    return v_p.extension(K0)
