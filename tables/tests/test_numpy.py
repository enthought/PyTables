import sys
import unittest
import os
import tempfile
import numpy
from numpy import *
from tables import *

from common import verbose, allequal, cleanup, heavy
import common

# To delete the internal attributes automagically
unittest.TestCase.tearDown = cleanup

typecodes = ['b', 'h', 'i', 'l', 'q', 'f', 'd']
# UInt64 checking disabled on win platforms
# because this type is not supported
if sys.platform != 'win32':
    typecodes += ['B', 'H', 'I', 'L', 'Q', 'F', 'D']
else:
    typecodes += ['B', 'H', 'I', 'L', 'F', 'D']
typecodes += ['b1']   # boolean

byteorder = {'little': '<', 'big': '>'}[sys.byteorder]

class BasicTestCase(unittest.TestCase):
    """Basic test for all the supported typecodes present in Numeric.
    All of them are included on pytables.
    """
    endiancheck = 0

    def WriteRead(self, testArray):
        if verbose:
            print '\n', '-=' * 30
            print "Running test for array with typecode '%s'" % \
                  testArray.dtype.char,
            print "for class check:", self.title

        # Create an instance of HDF5 Table
        self.file = tempfile.mktemp(".h5")
        self.fileh = openFile(self.file, mode = "w")
        self.root = self.fileh.root
        # Create the array under root and name 'somearray'
        a = testArray
        self.fileh.createArray(self.root, 'somearray', a, "Some array")

        # Close the file
        self.fileh.close()

        # Re-open the file in read-only mode
        self.fileh = openFile(self.file, mode = "r")
        self.root = self.fileh.root

        # Read the saved array
        b = self.root.somearray.read()
        # For cases that read returns a python type instead of a numpy type
        if not hasattr(b, "shape"):
            b = array(b, dtype=a.dtype.str)

        # Compare them. They should be equal.
        #if not allequal(a,b, "numpy") and verbose:
        if verbose:
            print "Array written:", a
            print "Array written shape:", a.shape
            print "Array written itemsize:", a.itemsize
            print "Array written type:", a.dtype.char
            print "Array read:", b
            print "Array read shape:", b.shape
            print "Array read itemsize:", b.itemsize
            print "Array read type:", b.dtype.char

        stype = self.root.somearray.stype
        # Check strictly the array equality
        assert type(a) == type(b)
        assert a.shape == b.shape
        assert a.shape == self.root.somearray.shape
        assert a.dtype == b.dtype
        if a.dtype.char[0] == "S":
            assert stype == "CharType"
        else:
            assert typeNA[a.dtype.type] == stype

        assert allequal(a,b, "numpy")
        self.fileh.close()
        # Then, delete the file
        os.remove(self.file)
        return

    def test00_char(self):
        "Data integrity during recovery (character objects)"

        a = array(self.tupleChar,'S'+str(len(self.tupleChar)))
        self.WriteRead(a)
        return

    def test01_char_nc(self):
        "Data integrity during recovery (non-contiguous character objects)"

        a = array(self.tupleChar,'S'+str(len(self.tupleChar)))
        if a.shape == ():
            b = a               # We cannot use the indexing notation
        else:
            b = a[::2]
            # Ensure that this numarray string is non-contiguous
            if a.shape[0] > 2:
                assert b.flags['CONTIGUOUS'] == False
        self.WriteRead(b)
        return

    def test02_types(self):
        "Data integrity during recovery (numerical types)"

        for typecode in typecodes:
            if self.tupleInt.shape:
                a = self.tupleInt.astype(typecode)
            else:
                # shape is the empty tuple ()
                a = array(self.tupleInt, dtype=typecode)
            self.WriteRead(a)

        return

    def test03_types_nc(self):
        "Data integrity during recovery (non-contiguous numerical types)"

        for typecode in typecodes:
            if self.tupleInt.shape:
                a = self.tupleInt.astype(typecode)
            else:
                # shape is the empty tuple ()
                a = array(self.tupleInt, dtype=typecode)
            # This should not be tested for the rank-0 case
            if len(a.shape) == 0:
                return
            b = a[::2]
            # Ensure that this array is non-contiguous (for non-trivial case)
            if a.shape[0] > 2:
                assert b.flags['CONTIGUOUS'] == False
            self.WriteRead(b)

        return


class Basic0DOneTestCase(BasicTestCase):
    # Rank-0 case
    title = "Rank-0 case 1"
    tupleInt = array(3)
    tupleChar = "4"

class Basic0DTwoTestCase(BasicTestCase):
    # Rank-0 case
    title = "Rank-0 case 2"
    tupleInt = array(33)
    tupleChar = "44"

class Basic1DOneTestCase(BasicTestCase):
    # 1D case
    title = "Rank-1 case 1"
    tupleInt = array((3,))
    tupleChar = ("a",)

class Basic1DTwoTestCase(BasicTestCase):
    # 1D case
    title = "Rank-1 case 2"
    tupleInt = array((0, 4))
    tupleChar = ("aaa",)

class Basic1DThreeTestCase(BasicTestCase):
    # 1D case
    title = "Rank-1 case 3"
    tupleInt = array((3, 4, 5))
    tupleChar = ("aaaa", "bbb",)

class Basic2DTestCase(BasicTestCase):
    # 2D case
    title = "Rank-2 case 1"
    #tupleInt = reshape(array(arange((4)**2)), (4,)*2)
    tupleInt = ones((4,)*2)
    tupleChar = [["aaa","ddddd"],["d","ss"],["s","tt"]]

class Basic10DTestCase(BasicTestCase):
    # 10D case
    title = "Rank-10 case 1"
    #tupleInt = reshape(array(arange((2)**10)), (2,)*10)
    tupleInt = ones((2,)*10)
    #tupleChar = reshape(array([1],dtype="S1"),(1,)*10)
    # The next tuple consumes far more time, so this
    # test should be run in heavy mode.
    tupleChar = array(tupleInt, dtype="S1")


# class Basic32DTestCase(BasicTestCase):
#     # 32D case (maximum)
#     tupleInt = reshape(array((22,)), (1,)*32)
#     # Strings seems to be very slow with somewhat large dimensions
#     # This should not be run unless the numarray people address this problem
#     # F. Altet 2006-01-04
#     tupleChar = array(tupleInt, dtype="S1")


class GroupsArrayTestCase(unittest.TestCase):
    """This test class checks combinations of arrays with groups.
    It also uses arrays ranks which ranges until 10.
    """

    def test00_iterativeGroups(self):
        """Checking combinations of arrays with groups
        It also uses arrays ranks which ranges until 10.
        """

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_iterativeGroups..." % \
                  self.__class__.__name__

        # Open a new empty HDF5 file
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, mode = "w")
        # Get the root group
        group = fileh.root

        i = 1
        for typecode in typecodes:
            # Create an array of typecode, with incrementally bigger ranges
            a = ones((2,) * i, typecode)
            # Save it on the HDF5 file
            dsetname = 'array_' + typecode
            if verbose:
                print "Creating dataset:", group._g_join(dsetname)
            hdfarray = fileh.createArray(group, dsetname, a, "Large array")
            # Create a new group
            group = fileh.createGroup(group, 'group' + str(i))
            # increment the range for next iteration
            i += 1

        # Close the file
        fileh.close()

        # Open the previous HDF5 file in read-only mode
        fileh = openFile(file, mode = "r")
        # Get the root group
        group = fileh.root

        # Get the metadata on the previosly saved arrays
        for i in range(1,len(typecodes)):
            # Create an array for later comparison
            a = ones((2,) * i, typecodes[i - 1])
            # Get the dset object hanging from group
            dset = getattr(group, 'array_' + typecodes[i-1])
            # Get the actual array
            b = dset.read()
            if not allequal(a,b, "numpy") and verbose:
                print "Array a original. Shape: ==>", a.shape
                print "Array a original. Data: ==>", a
                print "Info from dataset:", dset._v_pathname
                print "  shape ==>", dset.shape,
                print "  type ==> %s" % dset.type
                print "Array b read from file. Shape: ==>", b.shape,
                print ". Type ==> %s" % b.dtype.char

            assert a.shape == b.shape
            if dtype('l').itemsize == 4:
                if (a.dtype.char == "i" or a.dtype.char == "l"):
                    # Special expection. We have no way to distinguish between
                    # "l" and "i" typecode, and we can consider them the same
                    # to all practical effects
                    assert b.dtype.char == "l" or b.dtype.char == "i"
                elif (a.dtype.char == "I" or a.dtype.char == "L"):
                    # Special expection. We have no way to distinguish between
                    # "L" and "I" typecode, and we can consider them the same
                    # to all practical effects
                    assert b.dtype.char == "L" or b.dtype.char == "I"
                else:
                    assert allequal(a,b, "numpy")
            elif dtype('l').itemsize == 8:
                if (a.dtype.char == "q" or a.dtype.char == "l"):
                    # Special expection. We have no way to distinguish between
                    # "q" and "l" typecode in 64-bit platforms, and we can
                    # consider them the same to all practical effects
                    assert b.dtype.char == "l" or b.dtype.char == "q"
                elif (a.dtype.char == "Q" or a.dtype.char == "L"):
                    # Special expection. We have no way to distinguish between
                    # "Q" and "L" typecode in 64-bit platforms, and we can
                    # consider them the same to all practical effects
                    assert b.dtype.char == "L" or b.dtype.char == "Q"
                else:
                    assert allequal(a,b, "numpy")

            # Iterate over the next group
            group = getattr(group, 'group' + str(i))

        # Close the file
        fileh.close()

        # Then, delete the file
        os.remove(file)

    def test01_largeRankArrays(self):
        """Checking creation of large rank arrays (0 < rank <= 32)
        It also uses arrays ranks which ranges until maxrank.
        """

        # maximum level of recursivity (deepest group level) achieved:
        # maxrank = 32 (for a effective maximum rank of 32)
        # This limit is due to a limit in the HDF5 library.
        minrank = 1
        maxrank = 32

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_largeRankArrays..." % \
                  self.__class__.__name__
            print "Maximum rank for tested arrays:", maxrank
        # Open a new empty HDF5 file
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, mode = "w")
        group = fileh.root
        if verbose:
            print "Rank array writing progress: ",
        for rank in range(minrank, maxrank + 1):
            # Create an array of integers, with incrementally bigger ranges
            a = ones((1,) * rank, 'i')
            if verbose:
                print "%3d," % (rank),
            fileh.createArray(group, "array", a, "Rank: %s" % rank)
            group = fileh.createGroup(group, 'group' + str(rank))
        # Flush the buffers
        fileh.flush()
        # Close the file
        fileh.close()

        # Open the previous HDF5 file in read-only mode
        fileh = openFile(file, mode = "r")
        group = fileh.root
        if verbose:
            print
            print "Rank array reading progress: "
        # Get the metadata on the previosly saved arrays
        for rank in range(minrank, maxrank + 1):
            # Create an array for later comparison
            a = ones((1,) * rank, 'i')
            # Get the actual array
            b = group.array.read()
            if verbose:
                print "%3d," % (rank),
            if not a.tolist() == b.tolist() and verbose:
                print "Info from dataset:", dset._v_pathname
                print "  Shape: ==>", dset.shape,
                print "  typecode ==> %c" % dset.typecode
                print "Array b read from file. Shape: ==>", b.shape,
                print ". Type ==> %c" % b.dtype.char
            assert a.shape == b.shape
            if a.dtype.char == "i":
                # Special expection. We have no way to distinguish between
                # "l" and "i" typecode, and we can consider them the same
                # to all practical effects
                assert b.dtype.char == "l" or b.dtype.char == "i"
            else:
                assert a.dtype.char == b.dtype.char

            assert a == b

            # Iterate over the next group
            group = fileh.getNode(group, 'group' + str(rank))

        if verbose:
            print # This flush the stdout buffer
        # Close the file
        fileh.close()
        # Delete the file
        os.remove(file)


# Test Record class
class Record(IsDescription):
    var1  = StringCol(length=4, dflt="abcd", pos=0)
    var2  = StringCol(length=1, dflt="a", pos=1)
    var3  = BoolCol(1)  # Typecode == '1' in Numeric. 'B' in numarray
    var4  = Int8Col(1)
    var5  = UInt8Col(1)
    var6  = Int16Col(1)
    var7  = UInt16Col(1)
    var8  = Int32Col(1)
    var9  = UInt32Col(1)
    var10 = Int64Col(1)
    var11 = Float32Col(1.0)
    var12 = Float64Col(1.0)
    var13 = Complex32Col((1.+0.j))
    var14 = Complex64Col((1.+0.j))


class TableReadTestCase(common.PyTablesTestCase):
    nrows = 100

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        fileh = openFile(self.file, "w")
        table = fileh.createTable(fileh.root, 'table', Record)
        for i in range(self.nrows):
            table.row.append()  # Fill 100 rows with default values
        fileh.close()
        self.fileh = openFile(self.file, "r")

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)


    def test01_readTableChar(self):
        """Checking column conversion into NumPy in read(). Char flavor"""

        table = self.fileh.root.table
        for colname in table.colnames:
            numcol = table.read(field=colname, flavor="numpy")
            typecol = table.colstypes[colname]
            itemsizecol = table.description._v_itemsizes[colname]
            nctypecode = numcol.dtype.char
            if typecol == "CharType":
                if itemsizecol > 1:
                    orignumcol = array(['abcd']*self.nrows, dtype='S4')
                else:
                    orignumcol = array(['a']*self.nrows, dtype='S1')
                if verbose:
                    print "Typecode of NumPy column read:", nctypecode
                    print "Should look like:", 'c'
                    print "Itemsize of column:", itemsizecol
                    print "Shape of NumPy column read:", numcol.shape
                    print "Should look like:", orignumcol.shape
                    print "First 3 elements of read col:", numcol[:3]
                # Check that both NumPy objects are equal
                assert allequal(numcol, orignumcol, "numpy")

    def test01_readTableNum(self):
        """Checking column conversion into NumPy in read(). NumPy flavor"""

        table = self.fileh.root.table
        for colname in table.colnames:
            numcol = table.read(field=colname, flavor="numpy")
            typecol = table.colstypes[colname]
            nctypecode = typeNA[numcol.dtype.char[0]]
            if typecol <> "CharType":
                if verbose:
                    print "Typecode of NumPy column read:", nctypecode
                    print "Should look like:", typeNA[typecol]
                orignumcol = ones(shape=self.nrows, dtype=numcol.dtype.char)
                # Check that both NumPy objects are equal
                assert allequal(numcol, orignumcol, "numpy")


    def test02_readCoordsChar(self):
        """Column conversion into NumPy in readCoords(). Chars"""

        table = self.fileh.root.table
        coords = (1,2,3)
        self.nrows = len(coords)
        for colname in table.colnames:
            numcol = table.readCoordinates(coords, field=colname,
                                           flavor="numpy")
            typecol = table.colstypes[colname]
            itemsizecol = table.description._v_itemsizes[colname]
            nctypecode = numcol.dtype.char
            if typecol == "CharType":
                if itemsizecol > 1:
                    orignumcol = array(['abcd']*self.nrows, dtype='S4')
                else:
                    orignumcol = array(['a']*self.nrows, dtype='S1')
                if verbose:
                    print "Typecode of NumPy column read:", nctypecode
                    print "Should look like:", 'c'
                    print "Itemsize of column:", itemsizecol
                    print "Shape of NumPy column read:", numcol.shape
                    print "Should look like:", orignumcol.shape
                    print "First 3 elements of read col:", numcol[:3]
                # Check that both NumPy objects are equal
                assert allequal(numcol, orignumcol, "numpy")

    def test02_readCoordsNum(self):
        """Column conversion into NumPy in readCoordinates(). NumPy."""

        table = self.fileh.root.table
        coords = (1,2,3)
        self.nrows = len(coords)
        for colname in table.colnames:
            numcol = table.readCoordinates(coords, field=colname,
                                           flavor="numpy")
            typecol = table.colstypes[colname]
            type = numcol.dtype.type
            if typecol <> "CharType":
                if typecol == "Int64":
                    return
                if verbose:
                    print "Type of read NumPy column:", type
                    print "Should look like:", typeNA[typecol]
                orignumcol = ones(shape=self.nrows, dtype=numcol.dtype.char)
                # Check that both NumPy objects are equal
                assert allequal(numcol, orignumcol, "numpy")

    def test03_getIndexNumPy(self):
        """Getting table rows specifyied as NumPy scalar integers."""

        table = self.fileh.root.table
        coords = numpy.array([1,2,3], dtype='int8')
        for colname in table.colnames:
            numcol = [ table[coord][colname] for coord in coords ]
            typecol = table.colstypes[colname]
            if typecol <> "CharType":
                if typecol == "Int64":
                    return
                numcol = numpy.array(numcol, typeNA[typecol])
                if verbose:
                    type = numcol.dtype.type
                    print "Type of read NumPy column:", type
                    print "Should look like:", typeNA[typecol]
                orignumcol = ones(shape=len(numcol), dtype=numcol.dtype.char)
                # Check that both NumPy objects are equal
                assert allequal(numcol, orignumcol, "numpy")

    def test04_setIndexNumPy(self):
        """Setting table rows specifyied as NumPy integers."""

        self.fileh.close()
        self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        coords = numpy.array([1,2,3], dtype='int8')
        # Modify row 1
        table[coords[0]] = ["aasa","x"]+[232]*12
        #record = list(table[coords[0]])
        record = table.read(coords[0], flavor="numpy")
        if verbose:
            print """Original row:
['aasa', 'x', 232, -24, 232, 232, 1, 232L, 232, (232+0j), 232.0, 232L, (232+0j), 232.0]
"""
            print "Read row:\n", record
        assert record['var1'] == 'aasa'
        assert record['var2'] == 'x'
        assert record['var3'] == True
        assert record['var4'] == -24
        assert record['var7'] == 232


# The declaration of the nested table:
class Info(IsDescription):
    _v_pos = 3
    Name = StringCol(length=2)
    Value = Complex64Col()

class TestTDescr(IsDescription):

    """A description that has several nested columns."""

    _v_flavor = "numpy"     # The default would be returning numpy objects on reads
    x = Int32Col(0, shape=2, pos=0) #0
    y = FloatCol(1, shape=(2,2))
    z = UInt8Col(1)
    z3 = EnumCol({'r':4, 'g':2, 'b':1}, 'r', shape=2)
    color = StringCol(4, "ab", pos=2)
    info = Info()
    class Info(IsDescription): #1
        _v_pos = 1
        name = StringCol(length=2)
        value = Complex64Col(pos=0) #0
        y2 = FloatCol(pos=1) #1
        z2 = UInt8Col()
        class Info2(IsDescription):
            y3 = Time64Col(shape=2)
            name = StringCol(length=2)
            value = Complex64Col(shape=2)


class TableNativeFlavorTestCase(common.PyTablesTestCase):
    nrows = 100

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        fileh = openFile(self.file, "w")
        table = fileh.createTable(fileh.root, 'table', TestTDescr,
                                  expectedrows=self.nrows)
        for i in range(self.nrows):
            table.row.append()  # Fill 100 rows with default values
        table.flush()
        self.fileh = fileh

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)


    def _test01a_basicTableRead(self):
        """Checking the return of a NumPy in read()."""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        data = table[:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the value of some columns
        # A flat column
        col = table.cols.x[:3]
        assert isinstance(col, ndarray)
        npcol = zeros((3,2), dtype="int32")
        assert allequal(col, npcol, "numpy")
        # A nested column
        col = table.cols.Info[:3]
        assert isinstance(col, ndarray)
        dtype = [('value', '<c16'),
                 ('y2', '<f8'),
                 ('Info2',
                  [('name', '|S2'),
                   ('value', '<c16', (2,)),
                   ('y3', '<f8', (2,))]),
                 ('name', '|S2'),
                 ('z2', '|u1')]
        npcol = zeros((3,), dtype=dtype)
        assert col.dtype.descr == npcol.dtype.descr
        if verbose:
            print "col-->", col
            print "npcol-->", npcol
        # A copy() is needed in case the buffer can be in different segments
        assert col.copy().data == npcol.data

    def test01b_basicTableRead(self):
        """Checking the return of a NumPy in read() (strided version)."""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        data = table[::3]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the value of some columns
        # A flat column
        col = table.cols.x[:9:3]
        assert isinstance(col, ndarray)
        npcol = zeros((3,2), dtype="int32")
        assert allequal(col, npcol, "numpy")
        # A nested column
        col = table.cols.Info[:9:3]
        assert isinstance(col, ndarray)
        dtype = [('value', '%sc16' % byteorder),
                 ('y2', '%sf8' % byteorder),
                 ('Info2',
                  [('name', '|S2'),
                   ('value', '%sc16' % byteorder, (2,)),
                   ('y3', '%sf8' % byteorder, (2,))]),
                 ('name', '|S2'),
                 ('z2', '|u1')]
        npcol = zeros((3,), dtype=dtype)
        assert col.dtype.descr == npcol.dtype.descr
        if verbose:
            print "col-->", col
            print "npcol-->", npcol
        # A copy() is needed in case the buffer can be in different segments
        assert col.copy().data == npcol.data

    def test02_getWhereList(self):
        """Checking the return of NumPy in getWhereList method."""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        data = table.getWhereList('z == 1')
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 100
        # Finally, check that the contents are ok
        assert allequal(data, arange(100, dtype="i8"), "numpy")

    def test03a_readIndexed(self):
        """Checking the return of NumPy in readIndexed method (strings)."""

        table = self.fileh.root.table
        table.cols.color.createIndex(warn=1, testmode=1)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.readIndexed('color == "ab"')
        if verbose:
            print "Type of read:", type(data)
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == self.nrows

    def test03b_readIndexed(self):
        """Checking the return of NumPy in readIndexed method (numeric)."""

        table = self.fileh.root.table
        table.cols.z.createIndex(warn=1, testmode=1)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.readIndexed('z == 0')
        if verbose:
            print "Type of read:", type(data)
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 0

    def test04a_createTable(self):
        """Checking the Table creation from a numpy recarray."""

        dtype = [('value', '%sc16' % byteorder),
                 ('y2', '%sf8' % byteorder),
                 ('Info2',
                  [('name', '|S2'),
                   ('value', '%sc16' % byteorder, (2,)),
                   ('y3', '%sf8' % byteorder, (2,))]),
                 ('name', '|S2'),
                 ('z2', '|u1')]
        npdata = zeros((3,), dtype=dtype)
        table = self.fileh.createTable(self.fileh.root, 'table2', npdata)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table2
        data = table[:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npdata.dtype.descr
        if verbose:
            print "npdata-->", npdata
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == npdata.data

    def test04b_appendTable(self):
        """Checking appending a numpy recarray."""

        table = self.fileh.root.table
        npdata = table[3:6]
        table.append(npdata)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table[-3:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "Last 3 elements of read:", data[-3:]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npdata.dtype.descr
        if verbose:
            print "npdata-->", npdata
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == npdata.data

    def test05a_assignColumn(self):
        """Checking assigning to a column."""

        table = self.fileh.root.table
        table.cols.z[:] = zeros((100,), dtype='u1')
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.cols.z[:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 100
        # Finally, check that the contents are ok
        assert allequal(data, zeros((100,), dtype="u1"), "numpy")

    def test05b_modifyingColumns(self):
        """Checking modifying several columns at once."""

        table = self.fileh.root.table
        xcol = ones((3,2), 'int32')
        ycol = zeros((3,2,2), 'float64')
        zcol = zeros((3,), 'uint8')
        table.modifyColumns(3, 6, 1, [xcol, ycol, zcol], ['x', 'y', 'z'])
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.cols.y[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == ycol.data

    def test05c_modifyingColumns(self):
        """Checking modifying several columns using a single numpy buffer."""

        table = self.fileh.root.table
        dtype=[('x', 'i4', (2,)), ('y', 'f8', (2, 2)), ('z', 'u1')]
        nparray = zeros((3,), dtype=dtype)
        table.modifyColumns(3, 6, 1, nparray, ['x', 'y', 'z'])
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        ycol = zeros((3, 2, 2), 'float64')
        data = table.cols.y[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == ycol.data

    def test06a_assignNestedColumn(self):
        """Checking assigning a nested column (using modifyColumn)."""

        table = self.fileh.root.table
        dtype = [('value', '%sc16' % byteorder),
                 ('y2', '%sf8' % byteorder),
                 ('Info2',
                  [('name', '|S2'),
                   ('value', '%sc16' % byteorder, (2,)),
                   ('y3', '%sf8' % byteorder, (2,))]),
                 ('name', '|S2'),
                 ('z2', '|u1')]
        npdata = zeros((3,), dtype=dtype)
        data = table.cols.Info[3:6]
        table.modifyColumn(3, 6, 1, column=npdata, colname='Info')
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.cols.Info[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npdata.dtype.descr
        if verbose:
            print "npdata-->", npdata
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == npdata.data

    def test06b_assignNestedColumn(self):
        """Checking assigning a nested column (using the .cols accessor)."""

        table = self.fileh.root.table
        dtype = [('value', '%sc16' % byteorder),
                 ('y2', '%sf8' % byteorder),
                 ('Info2',
                  [('name', '|S2'),
                   ('value', '%sc16' % byteorder, (2,)),
                   ('y3', '%sf8' % byteorder, (2,))]),
                 ('name', '|S2'),
                 ('z2', '|u1')]
        npdata = zeros((3,), dtype=dtype)
#         self.assertRaises(NotImplementedError,
#                           table.cols.Info.__setitem__, slice(3,6,1),  npdata)
        table.cols.Info[3:6] = npdata
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        data = table.cols.Info[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npdata.dtype.descr
        if verbose:
            print "npdata-->", npdata
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert data.copy().data == npdata.data

    def test07a_modifyingRows(self):
        """Checking modifying several rows at once (using modifyRows)."""

        table = self.fileh.root.table
        # Read a chunk of the table
        chunk = table[0:3]
        # Modify it somewhat
        chunk['y'][:] = -1
        table.modifyRows(3, 6, 1, rows=chunk)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        ycol = zeros((3,2,2), 'float64')-1
        data = table.cols.y[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(ycol, data, "numpy")

    def test07b_modifyingRows(self):
        """Checking modifying several rows at once (using cols accessor)."""

        table = self.fileh.root.table
        # Read a chunk of the table
        chunk = table[0:3]
        # Modify it somewhat
        chunk['y'][:] = -1
        table.cols[3:6] = chunk
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        # Check that some column has been actually modified
        ycol = zeros((3,2,2), 'float64')-1
        data = table.cols.y[3:6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(ycol, data, "numpy")

    # XYX Descomentar aco despres de que el bug:
    # http://projects.scipy.org/scipy/numpy/ticket/314
    # s'haura solucionat
    def _test08a_modifyingRows(self):
        """Checking modifying just one row at once (using modifyRows)."""

        table = self.fileh.root.table
        # Read a chunk of the table
        chunk = table[3]
        # Modify it somewhat
        chunk['y'][:] = -1
        table.modifyRows(6, 7, 1, chunk)
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        # Check that some column has been actually modified
        ycol = zeros((2,2), 'float64')-1
        data = table.cols.y[6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(ycol, data, "numpy")

    # XYX Descomentar aco despres de que el bug:
    # http://projects.scipy.org/scipy/numpy/ticket/314
    # s'haura solucionat
    def _test08b_modifyingRows(self):
        """Checking modifying just one row at once (using cols accessor)."""

        table = self.fileh.root.table
        # Read a chunk of the table
        chunk = table[3]
        print "type(chunk)-->", type(chunk)
        # Modify it somewhat
        chunk['y'][:] = -1
        table.cols[6] = chunk
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            table = self.fileh.root.table
        # Check that some column has been actually modified
        ycol = zeros((2,2), 'float64')-1
        data = table.cols.y[6]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
            print "Length of the data read:", len(data)
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == ycol.dtype.descr
        if verbose:
            print "ycol-->", ycol
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(ycol, data, "numpy")

    def test09a_getStrings(self):
        """Checking the return of string columns with spaces."""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        rdata = table.getWhereList('color == "ab"')
        data = table.readCoordinates(rdata)
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 100
        # Finally, check that the contents are ok
        for idata in data['color']:
            assert idata == array("ab", dtype="|S4")

    def test09b_getStrings(self):
        """Checking the return of string columns with spaces. (modify)"""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        for i in range(50):
            table.cols.color[i] = "a  "
        table.flush()
        data = table[:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 100
        # Finally, check that the contents are ok
        for i in range(100):
            idata = data['color'][i]
            if i >= 50:
                assert idata == array("ab", dtype="|S4")
            else:
                assert idata == array("a  ", dtype="|S4")

    def test09c_getStrings(self):
        """Checking the return of string columns with spaces. (append)"""

        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        table = self.fileh.root.table
        row = table.row
        for i in range(50):
            row["color"] = "a  "   # note the trailing spaces
            row.append()
        table.flush()
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
        data = self.fileh.root.table[:]
        if verbose:
            print "Type of read:", type(data)
            print "Description of the record:", data.dtype.descr
            print "First 3 elements of read:", data[:3]
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check that all columns have been selected
        assert len(data) == 150
        # Finally, check that the contents are ok
        # Finally, check that the contents are ok
        for i in range(150):
            idata = data['color'][i]
            if i < 100:
                assert idata == array("ab", dtype="|S4")
            else:
                assert idata == array("a  ", dtype="|S4")

class TableNativeFlavorOpenTestCase(TableNativeFlavorTestCase):
    close = 0

class TableNativeFlavorCloseTestCase(TableNativeFlavorTestCase):
    close = 1

class AttributesTestCase(common.PyTablesTestCase):

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        self.fileh = openFile(self.file, "w")
        groups = self.fileh.createGroup(self.fileh.root, 'group')

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    def test01_writeAttribute(self):
        """Checking the creation of a numpy attribute."""
        g_attrs = self.fileh.root.group._v_attrs
        g_attrs.numpy1 = zeros((1,1), dtype='int16')
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            g_attrs = self.fileh.root.group._v_attrs
        # Check that we can retrieve a numpy object
        data = g_attrs.numpy1
        npcomp = zeros((1,1), dtype='int16')
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npcomp.dtype.descr
        if verbose:
            print "npcomp-->", npcomp
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(npcomp, data, "numpy")

    def test02_updateAttribute(self):
        """Checking the modification of a numpy attribute."""

        g_attrs = self.fileh.root.group._v_attrs
        g_attrs.numpy1 = zeros((1,2), dtype='int16')
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            g_attrs = self.fileh.root.group._v_attrs
        # Update this attribute
        g_attrs.numpy1 = ones((1,2), dtype='int16')
        # Check that we can retrieve a numpy object
        data = g_attrs.numpy1
        npcomp = ones((1,2), dtype='int16')
        # Check that both NumPy objects are equal
        assert isinstance(data, ndarray)
        # Check the type
        assert data.dtype.descr == npcomp.dtype.descr
        if verbose:
            print "npcomp-->", npcomp
            print "data-->", data
        # A copy() is needed in case the buffer would be in different segments
        assert allequal(npcomp, data, "numpy")

class AttributesOpenTestCase(AttributesTestCase):
    close = 0

class AttributesCloseTestCase(AttributesTestCase):
    close = 1

class StrlenTestCase(common.PyTablesTestCase):

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        self.fileh = openFile(self.file, "w")
        group = self.fileh.createGroup(self.fileh.root, 'group')
        tablelayout = {'_v_flavor':'numpy', 'Text': StringCol(length=1000),}
        self.table = self.fileh.createTable(group, 'table', tablelayout)
        row = self.table.row
        row['Text'] = 'Hello Francesc!'
        row.append()
        row['Text'] = 'Hola Francesc!'
        row.append()
        self.table.flush()

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    def test01(self):
        """Checking the lengths of strings (read field)."""
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            self.table = self.fileh.root.group.table
        # Get both strings
        str1 = self.table.col('Text')[0]
        str2 = self.table.col('Text')[1]
        if verbose:
            print "string1-->", str1
            print "string2-->", str2
        # Check that both NumPy objects are equal
        assert len(str1) == len('Hello Francesc!')
        assert len(str2) == len('Hola Francesc!')
        assert str1 == 'Hello Francesc!'
        assert str2 == 'Hola Francesc!'

    def test02(self):
        """Checking the lengths of strings (read recarray)."""
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            self.table = self.fileh.root.group.table
        # Get both strings
        str1 = self.table[:]['Text'][0]
        str2 = self.table[:]['Text'][1]
        # Check that both NumPy objects are equal
        assert len(str1) == len('Hello Francesc!')
        assert len(str2) == len('Hola Francesc!')
        assert str1 == 'Hello Francesc!'
        assert str2 == 'Hola Francesc!'


    def test03(self):
        """Checking the lengths of strings (read recarray, row by row)."""
        if self.close:
            self.fileh.close()
            self.fileh = openFile(self.file, "a")
            self.table = self.fileh.root.group.table
        # Get both strings
        str1 = self.table[0]['Text']
        str2 = self.table[1]['Text']
        # Check that both NumPy objects are equal
        assert len(str1) == len('Hello Francesc!')
        assert len(str2) == len('Hola Francesc!')
        assert str1 == 'Hello Francesc!'
        assert str2 == 'Hola Francesc!'


class StrlenOpenTestCase(StrlenTestCase):
    close = 0

class StrlenCloseTestCase(StrlenTestCase):
    close = 1


#--------------------------------------------------------

def suite():
    theSuite = unittest.TestSuite()
    niter = 1

    #theSuite.addTest(unittest.makeSuite(StrlenOpenTestCase))
    #theSuite.addTest(unittest.makeSuite(Basic0DOneTestCase))
    #theSuite.addTest(unittest.makeSuite(GroupsArrayTestCase))
    for i in range(niter):
        theSuite.addTest(unittest.makeSuite(Basic0DOneTestCase))
        theSuite.addTest(unittest.makeSuite(Basic0DTwoTestCase))
        theSuite.addTest(unittest.makeSuite(Basic1DOneTestCase))
        theSuite.addTest(unittest.makeSuite(Basic1DTwoTestCase))
        theSuite.addTest(unittest.makeSuite(Basic1DThreeTestCase))
        theSuite.addTest(unittest.makeSuite(Basic2DTestCase))
        theSuite.addTest(unittest.makeSuite(GroupsArrayTestCase))
        theSuite.addTest(unittest.makeSuite(TableReadTestCase))
        theSuite.addTest(unittest.makeSuite(TableNativeFlavorOpenTestCase))
        theSuite.addTest(unittest.makeSuite(TableNativeFlavorCloseTestCase))
        theSuite.addTest(unittest.makeSuite(AttributesOpenTestCase))
        theSuite.addTest(unittest.makeSuite(AttributesCloseTestCase))
        theSuite.addTest(unittest.makeSuite(StrlenOpenTestCase))
        theSuite.addTest(unittest.makeSuite(StrlenCloseTestCase))
        if heavy:
            theSuite.addTest(unittest.makeSuite(Basic10DTestCase))
            # The 32 dimensions case thakes forever to run!!
            # theSuite.addTest(unittest.makeSuite(Basic32DTestCase))
    return theSuite


if __name__ == '__main__':
    unittest.main( defaultTest='suite' )
