#!/usr/bin/env python

from nutils import *
import numpy, re
from math import gamma

class TestGaussQuadrature( object ):
  'Gaussian quadrature and exact integration on different element types'

  def _test( self, MAXORDER, elem, F, EPS=1e-12 ):
    funcstring = '*'.join(['x^%d','y^%d','z^%d'][:elem.ndims])
  
    for ab in numpy.ndindex( (MAXORDER,)*elem.ndims ):
      exact = F(*ab)
      order = sum(ab)
      log.info( ('\nIntegrating f = ' + funcstring + ', order = %d, elem = %s') % tuple(list(ab)+[order,elem]) )
      log.info( 'Exact: F = %8.6e' % exact )
      for p in range( 1, MAXORDER+1 ):
        name = 'gauss%d' % p
        points, weights = elem.eval( name )
  
        Fq = (weights*numpy.prod(points**numpy.array(ab)[_,:],axis=1)).sum()
  
        err = abs(Fq-exact)/exact
  
        log.info( '%s: n = %02d, F = %8.6e, rel.err. = %8.6e, %s' % (name,len(weights),Fq,err,'Exact' if err < EPS else 'Not exact') )
  
        criterion = p >= (1+numpy.amax(ab)//2 if isinstance( elem, element.QuadElement ) else order)
        if criterion:
          assert err < EPS, 'Integration should be exact'
        else:
          # Counterexamples can be constructed, but in the case of monomials with MAXORDER<8 this assert is verified
          assert err > EPS, 'Integration should not be exact'

  def test_lineelement( self ):
    MAXORDER = 7
    elem     = element.QuadElement( 1, vertices=[element.PrimaryVertex('test(%d)'%i) for i in range(2)] )
    F        = lambda a : 1./float(1+a)
  
    self._test ( MAXORDER, elem, F )

  def test_quadelement( self ):
    MAXORDER = 7
    elem     = element.QuadElement( 2, vertices=[element.PrimaryVertex('test(%d)'%i) for i in range(4)] )
    F        = lambda *args: numpy.prod(numpy.array(args)+1)**-1.

    self._test ( MAXORDER, elem, F )

  def test_hexelement( self ):
    MAXORDER = 7
    elem     = element.QuadElement( 3, vertices=[element.PrimaryVertex('test(%d)'%i) for i in range(8)] )
    F        = lambda *args: numpy.prod(numpy.array(args)+1)**-1.

    self._test ( MAXORDER, elem, F )

  def test_triangularelement( self ):
    MAXORDER = 7
    elem     = element.TriangularElement( vertices=[element.PrimaryVertex('test(%d)'%i) for i in range(3)] )
    F        = lambda a,b : gamma(1+a)*gamma(1+b)/gamma(3+a+b)

    self._test ( MAXORDER, elem, F )

  def test_tetrahedralelement( self ):
    MAXORDER = 8
    elem     = element.TetrahedronElement( vertices=[element.PrimaryVertex('test(%d)'%i) for i in range(4)] )
    F        = lambda a,b,c : gamma(1+a)*gamma(1+b)*gamma(1+c)/gamma(4+a+b+c)

    self._test ( MAXORDER, elem, F )

class TestSingularQuadrature( object ):
  'Singular bivariate quadrature and convergence on quadrilaterals'

  def __init__( self ):
    'Construct an arbitrary bivariate periodic structured mesh, only: shape > (2,2) for Element.neighbor() not to fail!'
    grid = lambda n: numpy.linspace( -numpy.pi, numpy.pi, n+1 )
    self.dims = 3, 4
    self.domain, self.coords = mesh.rectilinear( tuple(grid(n) for n in self.dims) )
    self.ddomain = self.domain * self.domain
    self.domainp, self.coordsp = mesh.rectilinear( tuple(grid(n) for n in self.dims), periodic=(0, 1) )
    self.ddomainp = self.domainp * self.domainp

  def test_connectivity( self ):
    'Test implementation of Element.neighbor()'
    elem0 = self.domainp.structure.flat[0]
    m, n = self.dims
    neighbor = {0:0,
                1:1, n-1:1, n:1, n*(m-1):1,
              n+1:2, 2*n-1:2, n*(m-1)+1:2, n*m-1:2}
    for i, elem in enumerate( self.domainp ):
      assert elem0.neighbor( elem ) == neighbor.get( i, -1 ), \
        'Error with neighbor detection'

  def test_orientations( self ):
    'Test rotations of local coordinates to align singularities to singular integration scheme'
    m, n = self.dims
    divide = lambda num, den: (num//den, num%den)
    # ordering of neighbors inside transf
    # 5-4-3
    # |   |
    # 6 0 2
    # |  \|
    # 7-8 1
    transf = {(0,0):(0,0),                                                  # 0
             (1,-1):(3,1), (1-m,-1):(3,1), (1-m,n-1):(3,1),  (1,n-1):(3,1), # 1
              (1,0):(3,1),  (1-m,0):(3,1),                                  # 2
              (1,1):(2,0),  (1-m,1):(2,0), (1-m,1-n):(2,0),  (1,1-n):(2,0), # 3
              (0,1):(2,0),  (0,1-n):(2,0),                                  # 4
             (-1,1):(1,3),  (m-1,1):(1,3), (m-1,1-n):(1,3), (-1,1-n):(1,3), # 5
             (-1,0):(1,3),  (m-1,0):(1,3),                                  # 6
            (-1,-1):(0,2), (m-1,-1):(0,2), (m-1,n-1):(0,2), (-1,n-1):(0,2), # 7
             (0,-1):(0,2),  (0,n-1):(0,2)}                                  # 8
        
    for i, elem in enumerate( self.ddomainp ):
      # coords of elem1 and elem2
      ijx, ijy = divide( i, m*n )
      ix, jx = divide( ijx, n )
      iy, jy = divide( ijy, n )
      # transforms for periodic, structured grid
      transform1, transform2 = transf.get( (iy-ix, jy-jx), (0, 0) )
      assert elem.orientation[1:] == (transform1, transform2), 'Error with reorientation'

  def test_transformations( self ):
    'Test transformations performed on gauss schemes'
    ischeme = 'gauss3'
    neighbor = 1
    # Get all types
    elems = {}
    tlist = set(range(4))
    for i, elem in enumerate( self.ddomainp ):
      n, t1, t2 = elem.orientation
      if n==neighbor:
        try:
          tlist.remove(t1)
          elems[t1] = elem
          if not len(tlist): break
        except IndexError:
          pass

    # Alternative coordinate computation
    points, weights = elem.get_quad_bem_ischeme( ischeme, neighbor )
    rotate = [numpy.array( [ [1, 0],  [0, 1]] ), 
              numpy.array( [ [0, 1], [-1, 0]] ), 
              numpy.array( [[-1, 0], [0, -1]] ), 
              numpy.array( [[0, -1],  [1, 0]] )]
    shift = [numpy.array( [0, 0] ),
             numpy.array( [0, 1] ),
             numpy.array( [1, 1] ),
             numpy.array( [1, 0] )]
    transform = lambda points, transf: (
        points[:,:,_] * rotate[transf].T[_,:,:]).sum(1) + shift[transf][_,:]

    for t1, elem in elems.iteritems():
      t2 = numpy.mod( t1+2, 4 ) # only for StructuredTopology
      # See if ProductElement.singular_ischeme_quad() gives same result
      points_ref = numpy.empty( points.shape )
      points_ref[:,:2] = transform( points[:,:2], t1 )
      points_ref[:,2:] = transform( points[:,2:], t2 )
      points_test = elem.singular_ischeme_quad( orientation=elem.orientation, ischeme=ischeme )[0]
      assert numpy.linalg.norm( points_ref-points_test ) < 1.e-14

      # See if inverse transformation brings back to points[0]
      points_inv = numpy.empty( points.shape )
      t1inv = [0, 3, 2, 1][t1]
      t2inv = [0, 3, 2, 1][t2]
      points_inv[:,:2] = transform( points_test[:,:2], t1inv )
      points_inv[:,2:] = transform( points_test[:,2:], t2inv )
      assert numpy.linalg.norm( points-points_inv ) < 1.e-14

  def _integrate( self, func, geom='torus', qset=range(1,9), qmax=16, slopes=None ):
    '''Test convergence of approximation on all product element types.
    I: func,   integrand,
       geom,   domain of integration,
       qset,   set of quadrature orders, length (1,2, >2) determines type of test,
       qmax,   reference quadrature level,
       slopes, expected rate of convergence.'''
    m, n = self.dims
    plot_quad_points = False
    compare_to_gauss = False

    # geometry and topology need same periodicity for singular scheme to work!
    if geom is 'torus':
      domain, ddomain = self.domainp, self.ddomainp
      R, r = 3, 1
      assert R > r, 'No self-intersection admitted'
      phi, theta = self.coordsp
      geom = function.stack( [
          function.cos(phi) * (r*function.cos(theta) + R),
          function.sin(phi) * (r*function.cos(theta) + R),
          function.sin(theta) * r] )

    if geom is 'hull':
      domain, ddomain = self.domain, self.ddomain
      x, y = .5*(self.coords/numpy.pi + 1)*self.dims - 1.5 # ensure elem@(1,1) centered
      geom = function.stack( [x, y, x**2*y**2] )

    else:
      domain, ddomain = self.domain, self.ddomain
      geom = .5*(self.coords/numpy.pi + 1)*self.dims # rescale: elem.vol.=1, shift: coords>0

    # stuff I think could be handled underwater by Topology.integrate?
    iw = function.iwscale( geom, domain.ndims )
    iweights = iw * function.opposite( iw ) * function.IWeights()

    # all possible different schemes and transformations
    assert m>2 and n>3, 'Insufficient mesh size for all element types to be present.'
    index = (m*n+1)*(n+1) + numpy.array( [0, -n, -1, 1, n, -n-1, -n+1, n-1, n+1, 2] )
    ecoll = [{}, {}, {}, {}]
    for i, elem in enumerate( ddomain ):
      if not i in index: continue
      ecoll[elem.orientation[0]][elem.orientation[1:]] = elem

    # integrands and primitives
    devel = len(qset) > 2
    for neighbor, elems in enumerate( ecoll ):
      if devel: errs, Fset = {}, {}
      if compare_to_gauss: errsg = {}
      for key, elem in elems.iteritems():
        topo = topology.UnstructuredTopology( [elem], ndims=2 )
        F = topo.integrate( func(geom), iweights=iweights, ischeme='singular%i'%qmax )
        if compare_to_gauss:
          A = {0:8, 1:6, 2:4, 3:1}[neighbor]
          qg = int(qmax*(A**.25))
          Fg = topo.integrate( func(geom), iweights=iweights, ischeme='gauss%i'%qg )
        if plot_quad_points: # Plot integration points
          with plot.PyPlot( 'quad' ) as fig:
            pts, wts = elem.eval( 'singular%i'%3 )
            z = key[0]%2
            pts[:,z] *= -1
            pts[:,z] += 1
            affine = [int(n) for n in re.findall( r'\d+', elem.elem1.vertices[0].id )]
            fig.plot( pts[:,0] + affine[0] - 1.5,
                      pts[:,1] + affine[1] - 1.5, 'rx' )
            affine = [int(n) for n in re.findall( r'\d+', elem.elem2.vertices[0].id )]
            fig.plot( pts[:,2] + affine[0] - 1.5,
                      pts[:,3] + affine[1] - 1.5, 'g+' )
            for x in range( 4 ): fig.plot( [x-1.5, x-1.5], [-1.5, 2.5], 'b-' )
            for y in range( 5 ): fig.plot( [-1.5, 1.5], [y-1.5, y-1.5], 'b-' )
            fig.title( 'n:%i, t:%i, %i'%elem.orientation )
            fig.axes().set_aspect('equal', 'datalim')

        if devel:
          # Devel mode (default), visual check of convergence
          Fset[key] = F
          errs[key] = []
          if compare_to_gauss: errsg[key] = []
          for q in qset:
            Fq = topo.integrate( func(geom), iweights=iweights, ischeme='singular%i'%q )
            errs[key].append( numpy.abs(F/Fq-1) )
            if compare_to_gauss:
              qg = int(q*(A**.25))
              Fgq = topo.integrate( func(geom), iweights=iweights, ischeme='gauss%i'%qg )
              errsg[key].append( numpy.abs(Fg/Fgq-1) )

        elif len(qset) == 1:
          # Test assertions on exact quadrature
          Fq = topo.integrate( func(geom), iweights=iweights, ischeme='singular%i'%qset[0] )
          err = numpy.abs(F/Fq-1)
          assert err < 1.e-12, 'Nonexact quadrature, err = %.1e' % err

        elif len(qset) == 2:
          # Test assertions on convergence rate of quadrature
          q0, q1 = tuple( qset )
          F0 = topo.integrate( func(geom), iweights=iweights, ischeme='singular%i'%q0 )
          F1 = topo.integrate( func(geom), iweights=iweights, ischeme='singular%i'%q1 )
          err0 = numpy.abs(F/F0-1)
          err1 = numpy.abs(F/F1-1)
          slope = numpy.log10(err1/err0)/(q1-q0)
          print slopes, slope, ' | ', neighbor, key
          assert slope <= (-2. if slopes is None else slopes[neighbor]) or err1 < 1.e-12, \
              'Insufficient quadrature convergence (is func analytic?), slope = %.2f' % slope

        else:
          raise ValueError( 'Range of quadrature orders should contain >=1 value.' )

      if devel:
        with plot.PyPlot( 'conv' ) as fig:
          style = 'x-', '+-', '*-', '.-'
          styleg = 'x:', '+:', '*:', '.:'
          for key, val in errs.iteritems():
            label = 't:%i,%i'%key+' F=%.3e'%Fset[key]
            fig.semilogy( qset, val, style[key[0]], label=label )
            if neighbor and compare_to_gauss: fig.semilogy( qset, errsg[key], styleg[key[0]], label=label+' [g]' )
          i = len(qset)//2
          fig.slope_triangle( qset[i::i-1][::-1], val[i::i-1][::-1], slopefmt='{0:.2f}' )
          fig.title( 'n-type: %i'%(-1 if neighbor is 3 else neighbor) )
          fig.legend( loc='lower left' )

  def test_constantfunc( self ):
    'Exact integration of a constant integrand, acc to theory'
    # Theory predicts exact integration of f in P^p if q >= 2+(p+1)//2, for singular scheme on quad elements
    # In this formula f = sum_{i<4} c_i x_i^{p_i} and p := \max p_i
    self._integrate( lambda x: 1, geom='coords', qset=(2,), qmax=16 )

  def test_linearfunc( self ):
    'Exact integration of a linear integrand, acc to theory'
    y = function.opposite
    self._integrate( lambda x: (x+y(x)).sum(), geom='coords', qset=(3,), qmax=16 )

  def test_quadraticfunc( self ):
    'Exact integration of a quadratic integrand, acc to theory'
    y = function.opposite
    self._integrate( lambda x: ((x+y(x))**2).sum(), geom='coords', qset=(3,), qmax=16 )

  def test_nonexactfunc( self ):
    'Quadrature convergence for non-polynomial analytic func (det grad torus), acc to theory'
    self._integrate( lambda x: 1, geom='torus', qset=(5,6), qmax=16 )

  def test_cosinefunc( self ):
    'Quadrature convergence for non-polynomial analytic func (cosine), acc to theory'
    y = function.opposite
    cos = function.cos
    prod = lambda f: function.product( f, -1 )
    self._integrate( lambda x: prod(cos(x))*prod(cos(y(x))), geom='coords', qset=(5,6), qmax=16 )

  def test_weaklysingularfunc( self ):
    'Quadrature convergence for a singular singular func'
    func = lambda x: function.norm2( x-function.opposite(x) )**-1
    self._integrate( func, geom='hull', qset=(6,10), qmax=16, slopes=(-1., -.4, -.8, -.2) )

  def test_stronglysingularfunc( self ):
    'Cauchy Principal Value of a strongly singular func'
    func = lambda x: function.norm2( x-function.opposite(x) )**-2
    self._integrate( func, geom='hull', qset=(6,10), qmax=16, slopes=(-.1, -.4, -.6, -.2) )

def visualinspect():
  'Visual inspection of singular quadrature convergence: for tests calling _integrate(), remove the qset argument'
  visual = TestSingularQuadrature()
  visual.test_stronglysingularfunc()

if __name__ == '__main__':
  util.run( visualinspect )

# vim:shiftwidth=2:foldmethod=indent:foldnestmax=2