import unittest, numpy, contextlib
from nutils import sparse


@contextlib.contextmanager
def chunksize(n):
  chunksize = sparse.chunksize
  try:
    sparse.chunksize = n
    yield
  finally:
    sparse.chunksize = chunksize


class vector(unittest.TestCase):

  def setUp(self):
    self.data = numpy.array(
      [((4,), 10),
       ((4,), 20),
       ((3,),  1),
       ((2,), 30),
       ((1,), 40),
       ((2,), 50),
       ((3,), -1),
       ((0,),  0),
       ((0,), 60)], dtype=sparse.dtype([5], int))
    self.full = numpy.array(
      [ 60, 40, 80,  0, 30 ])

  def test_ndim(self):
    self.assertEqual(sparse.ndim(self.data), 1)

  def test_shape(self):
    self.assertEqual(sparse.shape(self.data), (5,))

  def test_indices(self):
    i0, = sparse.indices(self.data)
    self.assertEqual(i0.tolist(), [4, 4, 3, 2, 1, 2, 3, 0, 0])

  def test_values(self):
    v = sparse.values(self.data)
    self.assertEqual(v.tolist(), [10, 20, 1, 30, 40, 50, -1, 0, 60])

  def test_extract(self):
    indices, values, shape = sparse.extract(self.data)
    self.assertEqual(indices[0].tolist(), sparse.indices(self.data)[0].tolist())
    self.assertEqual(values.tolist(), sparse.values(self.data).tolist())
    self.assertEqual(shape, sparse.shape(self.data))

  def test_dedup(self):
    for inplace in False, True:
      with self.subTest(inplace=inplace), chunksize(self.data.itemsize * 3):
        dedup = sparse.dedup(self.data, inplace=inplace)
        (self.assertIs if inplace else self.assertIsNot)(dedup, self.data)
        self.assertEqual(dedup.tolist(),
          [((0,),60), ((1,),40), ((2,),80), ((3,),0), ((4,),30)])

  def test_prune(self):
    for inplace in False, True:
      with self.subTest(inplace=inplace), chunksize(self.data.itemsize * 3):
        prune = sparse.prune(self.data, inplace=inplace)
        (self.assertIs if inplace else self.assertIsNot)(prune, self.data)
        self.assertEqual(prune.tolist(),
          [((4,),10), ((4,),20), ((3,),1), ((2,),30), ((1,),40), ((2,),50), ((3,),-1), ((0,),60)])

  def test_toarray(self):
    array = sparse.toarray(self.data)
    self.assertEqual(array.tolist(), self.full.tolist())

  def test_convert(self):
    self.assertIsInstance(sparse.convert(self.data), numpy.ndarray)

  def test_add_int(self):
    other = numpy.array([
      ((1,), -40),
      ((2,),  70)], dtype=self.data.dtype)
    retval = sparse.add([self.data, other])
    self.assertEqual(retval.dtype, self.data.dtype)
    self.assertEqual(retval.tolist(),
      [((4,),10), ((4,),20), ((3,),1), ((2,),30), ((1,),40), ((2,),50), ((3,),-1), ((0,),0), ((0,),60), ((1,),-40), ((2,),70)])

  def test_add_float(self):
    other = numpy.array([
      ((1,), -40),
      ((2,),  .5)], dtype=sparse.dtype((5,), float))
    retval = sparse.add([self.data, other])
    self.assertEqual(retval.dtype, other.dtype)
    self.assertEqual(retval.tolist(),
      [((4,),10), ((4,),20), ((3,),1), ((2,),30), ((1,),40), ((2,),50), ((3,),-1), ((0,),0), ((0,),60), ((1,),-40), ((2,),.5)])

class matrix(unittest.TestCase):

  def setUp(self):
    self.data = numpy.array([
      ((2,4), 10),
      ((3,4), 20),
      ((2,3),  1),
      ((1,2), 30),
      ((0,1), 40),
      ((1,2), 50),
      ((2,3), -1),
      ((3,0),  0),
      ((2,0), 60)], dtype=sparse.dtype([4,5], int))
    self.full = numpy.array(
      [[  0, 40,  0,  0,  0 ],
       [  0,  0, 80,  0,  0 ],
       [ 60,  0,  0,  0, 10 ],
       [  0,  0,  0,  0, 20 ]])

  def test_ndim(self):
    self.assertEqual(sparse.ndim(self.data), 2)

  def test_shape(self):
    self.assertEqual(sparse.shape(self.data), (4,5))

  def test_indices(self):
    i0, i1 = sparse.indices(self.data)
    self.assertEqual(i0.tolist(), [2, 3, 2, 1, 0, 1, 2, 3, 2])
    self.assertEqual(i1.tolist(), [4, 4, 3, 2, 1, 2, 3, 0, 0])

  def test_values(self):
    v = sparse.values(self.data)
    self.assertEqual(v.tolist(), [10, 20, 1, 30, 40, 50, -1, 0, 60])

  def test_extract(self):
    indices, values, shape = sparse.extract(self.data)
    self.assertEqual(indices[0].tolist(), sparse.indices(self.data)[0].tolist())
    self.assertEqual(indices[1].tolist(), sparse.indices(self.data)[1].tolist())
    self.assertEqual(values.tolist(), sparse.values(self.data).tolist())
    self.assertEqual(shape, sparse.shape(self.data))

  def test_dedup(self):
    for inplace in False, True:
      with self.subTest(inplace=inplace), chunksize(self.data.itemsize * 3):
        dedup = sparse.dedup(self.data, inplace=inplace)
        (self.assertIs if inplace else self.assertIsNot)(dedup, self.data)
        self.assertEqual(dedup.tolist(),
          [((0,1),40), ((1,2),80), ((2,0),60), ((2,3),0), ((2,4),10), ((3,0),0), ((3,4),20)])

  def test_prune(self):
    for inplace in False, True:
      with self.subTest(inplace=inplace), chunksize(self.data.itemsize * 3):
        prune = sparse.prune(self.data, inplace=inplace)
        (self.assertIs if inplace else self.assertIsNot)(prune, self.data)
        self.assertEqual(prune.tolist(),
          [((2,4),10), ((3,4),20), ((2,3),1), ((1,2),30), ((0,1),40), ((1,2),50), ((2,3),-1), ((2,0),60)])

  def test_toarray(self):
    array = sparse.toarray(self.data)
    self.assertEqual(array.tolist(), self.full.tolist())

  def test_tomatrix(self):
    from nutils import matrix
    with matrix.Numpy():
      dense = sparse.tomatrix(self.data).export('dense')
    self.assertEqual(dense.tolist(), self.full.tolist())

  def test_convert(self):
    from nutils import matrix
    with matrix.Numpy():
      self.assertIsInstance(sparse.convert(self.data), matrix.Matrix)

  def test_add_int(self):
    other = numpy.array([
      ((0, 1), -40),
      ((0, 2),  70)], dtype=self.data.dtype)
    retval = sparse.add([self.data, other])
    self.assertEqual(retval.dtype, self.data.dtype)
    self.assertEqual(retval.tolist(),
      [((2,4),10), ((3,4),20), ((2,3),1), ((1,2),30), ((0,1),40), ((1,2),50), ((2,3),-1), ((3,0),0), ((2,0),60), ((0,1),-40), ((0,2),70)])

  def test_add_float(self):
    other = numpy.array([
      ((0, 1), -40),
      ((0, 2),  .5)], dtype=sparse.dtype((4,5), float))
    retval = sparse.add([self.data, other])
    self.assertEqual(retval.dtype, other.dtype)
    self.assertEqual(retval.tolist(),
      [((2,4),10), ((3,4),20), ((2,3),1), ((1,2),30), ((0,1),40), ((1,2),50), ((2,3),-1), ((3,0),0), ((2,0),60), ((0,1),-40), ((0,2),.5)])
