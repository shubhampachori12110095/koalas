#
# Copyright (C) 2019 Databricks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import inspect
import unittest

import numpy as np
import pandas as pd

from databricks import koalas
from databricks.koalas.testing.utils import ReusedSQLTestCase, TestUtils
from databricks.koalas.exceptions import PandasNotImplementedError
from databricks.koalas.missing.frame import _MissingPandasLikeDataFrame
from databricks.koalas.missing.series import _MissingPandasLikeSeries
from databricks.koalas.series import Series


class DataFrameTest(ReusedSQLTestCase, TestUtils):

    @property
    def full(self):
        return pd.DataFrame({
            'a': [1, 2, 3, 4, 5, 6, 7, 8, 9],
            'b': [4, 5, 6, 3, 2, 1, 0, 0, 0],
        }, index=[0, 1, 3, 5, 6, 8, 9, 9, 9])

    @property
    def df(self):
        return koalas.from_pandas(self.full)

    def test_Dataframe(self):
        d = self.df
        full = self.full

        expected = pd.Series([2, 3, 4, 5, 6, 7, 8, 9, 10],
                             index=[0, 1, 3, 5, 6, 8, 9, 9, 9],
                             name='(a + 1)')  # TODO: name='a'

        self.assert_eq(d['a'] + 1, expected)

        self.assert_eq(d.columns, pd.Index(['a', 'b']))

        self.assert_eq(d[d['b'] > 2], full[full['b'] > 2])
        self.assert_eq(d[['a', 'b']], full[['a', 'b']])
        self.assert_eq(d.a, full.a)
        # TODO: assert d.b.mean().compute() == full.b.mean()
        # TODO: assert np.allclose(d.b.var().compute(), full.b.var())
        # TODO: assert np.allclose(d.b.std().compute(), full.b.std())

        assert repr(d)

        df = pd.DataFrame({
            'a': [1, 2, 3, 4, 5, 6, 7, 8, 9],
            'b': [4, 5, 6, 3, 2, 1, 0, 0, 0],
        })
        ddf = koalas.from_pandas(df)
        self.assert_eq(df[['a', 'b']], ddf[['a', 'b']])

        self.assertEqual(ddf.a.notnull().alias("x").name, "x")

    def test_head_tail(self):
        d = self.df
        full = self.full

        self.assert_eq(d.head(2), full.head(2))
        self.assert_eq(d.head(3), full.head(3))
        self.assert_eq(d['a'].head(2), full['a'].head(2))
        self.assert_eq(d['a'].head(3), full['a'].head(3))

        # TODO: self.assert_eq(d.tail(2), full.tail(2))
        # TODO: self.assert_eq(d.tail(3), full.tail(3))
        # TODO: self.assert_eq(d['a'].tail(2), full['a'].tail(2))
        # TODO: self.assert_eq(d['a'].tail(3), full['a'].tail(3))

    def test_index_head(self):
        d = self.df
        full = self.full

        self.assert_eq(list(d.index.head(2).toPandas()), list(full.index[:2]))
        self.assert_eq(list(d.index.head(3).toPandas()), list(full.index[:3]))

    def test_Series(self):
        d = self.df
        full = self.full

        self.assertTrue(isinstance(d.a, Series))
        self.assertTrue(isinstance(d.a + 1, Series))
        self.assertTrue(isinstance(1 + d.a, Series))
        # TODO: self.assert_eq(d + 1, full + 1)

    def test_Index(self):
        for case in [pd.DataFrame(np.random.randn(10, 5), index=list('abcdefghij')),
                     pd.DataFrame(np.random.randn(10, 5),
                                  index=pd.date_range('2011-01-01', freq='D',
                                                      periods=10))]:
            ddf = koalas.from_pandas(case)
            self.assert_eq(list(ddf.index.toPandas()), list(case.index))

    def test_attributes(self):
        d = self.df

        self.assertIn('a', dir(d))
        self.assertNotIn('foo', dir(d))
        self.assertRaises(AttributeError, lambda: d.foo)

        df = koalas.DataFrame({'a b c': [1, 2, 3]})
        self.assertNotIn('a b c', dir(df))
        df = koalas.DataFrame({'a': [1, 2], 5: [1, 2]})
        self.assertIn('a', dir(df))
        self.assertNotIn(5, dir(df))

    def test_column_names(self):
        d = self.df

        self.assert_eq(d.columns, pd.Index(['a', 'b']))
        self.assert_eq(d[['b', 'a']].columns, pd.Index(['b', 'a']))
        self.assertEqual(d['a'].name, 'a')
        self.assertEqual((d['a'] + 1).name, '(a + 1)')  # TODO: 'a'
        self.assertEqual((d['a'] + d['b']).name, '(a + b)')  # TODO: None

    def test_index_names(self):
        d = self.df

        # TODO?: self.assertIsNone(d.index.name)

        idx = pd.Index([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], name='x')
        df = pd.DataFrame(np.random.randn(10, 5), idx)
        ddf = koalas.from_pandas(df)
        self.assertEqual(ddf.index.name, 'x')

    def test_rename_columns(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5, 6, 7],
                           'b': [7, 6, 5, 4, 3, 2, 1]})
        ddf = koalas.from_pandas(df)

        ddf.columns = ['x', 'y']
        df.columns = ['x', 'y']
        self.assert_eq(ddf.columns, pd.Index(['x', 'y']))
        self.assert_eq(ddf, df)

        msg = "Length mismatch: Expected axis has 2 elements, new values have 4 elements"
        with self.assertRaisesRegex(ValueError, msg):
            ddf.columns = [1, 2, 3, 4]

        # Multi-index columns
        df = pd.DataFrame({('A', '0'): [1, 2, 2, 3], ('B', 1): [1, 2, 3, 4]})
        ddf = koalas.from_pandas(df)

        df.columns = ['x', 'y']
        ddf.columns = ['x', 'y']
        self.assert_eq(ddf.columns, pd.Index(['x', 'y']))
        self.assert_eq(ddf, df)

    def test_rename_series(self):
        s = pd.Series([1, 2, 3, 4, 5, 6, 7], name='x')
        ds = koalas.from_pandas(s)

        s.name = 'renamed'
        ds.name = 'renamed'
        self.assertEqual(ds.name, 'renamed')
        self.assert_eq(ds, s)

        ind = s.index
        dind = ds.index
        ind.name = 'renamed'
        dind.name = 'renamed'
        self.assertEqual(ind.name, 'renamed')
        self.assert_eq(list(dind.toPandas()), list(ind))

    def test_rename_series_method(self):
        # Series name
        s = pd.Series([1, 2, 3, 4, 5, 6, 7], name='x')
        ds = koalas.from_pandas(s)

        self.assert_eq(ds.rename('y'), s.rename('y'))
        self.assertEqual(ds.name, 'x')  # no mutation
        # self.assert_eq(ds.rename(), s.rename())

        ds.rename('z', inplace=True)
        s.rename('z', inplace=True)
        self.assertEqual(ds.name, 'z')
        self.assert_eq(ds, s)

        # Series index
        s = pd.Series(['a', 'b', 'c', 'd', 'e', 'f', 'g'], name='x')
        ds = koalas.from_pandas(s)

        # TODO: index
        # res = ds.rename(lambda x: x ** 2)
        # self.assert_eq(res, s.rename(lambda x: x ** 2))

        # res = ds.rename(s)
        # self.assert_eq(res, s.rename(s))

        # res = ds.rename(ds)
        # self.assert_eq(res, s.rename(s))

        # res = ds.rename(lambda x: x**2, inplace=True)
        # self.assertis(res, ds)
        # s.rename(lambda x: x**2, inplace=True)
        # self.assert_eq(ds, s)

    def test_stat_functions(self):
        df = pd.DataFrame({'A': [1, 2, 3, 4],
                           'B': [1.0, 2.1, 3, 4]})
        ddf = koalas.from_pandas(df)

        functions = ['max', 'min', 'mean', 'sum']
        for funcname in functions:
            self.assertEqual(getattr(ddf.A, funcname)(), getattr(df.A, funcname)())
            self.assert_eq(getattr(ddf, funcname)(), getattr(df, funcname)())

        functions = ['std', 'var']
        for funcname in functions:
            self.assertAlmostEqual(getattr(ddf.A, funcname)(), getattr(df.A, funcname)())
            self.assertPandasAlmostEqual(getattr(ddf, funcname)(), getattr(df, funcname)())

        # NOTE: To test skew and kurt, just make sure they run.
        #       The numbers are different in spark and pandas.
        functions = ['skew', 'kurt']
        for funcname in functions:
            getattr(ddf.A, funcname)()
            getattr(ddf, funcname)()

    def test_count(self):
        df = pd.DataFrame({'A': [1, 2, 3, 4],
                           'B': [1.0, 2.1, 3, 4]})
        ddf = koalas.from_pandas(df)

        # NOTE: This does not patch the pandas API, but maintains compat with spark
        self.assertEqual(ddf.count(), len(df))

        self.assertEqual(ddf.A.count(), df.A.count())

    def test_dropna(self):
        df = pd.DataFrame({'x': [np.nan, 2, 3, 4, np.nan, 6],
                           'y': [1, 2, np.nan, 4, np.nan, np.nan],
                           'z': [1, 2, 3, 4, np.nan, np.nan]},
                          index=[10, 20, 30, 40, 50, 60])
        ddf = koalas.from_pandas(df)

        self.assert_eq(ddf.x.dropna(), df.x.dropna())
        self.assert_eq(ddf.y.dropna(), df.y.dropna())
        self.assert_eq(ddf.z.dropna(), df.z.dropna())

        self.assert_eq(ddf.dropna(), df.dropna())
        self.assert_eq(ddf.dropna(how='all'), df.dropna(how='all'))
        self.assert_eq(ddf.dropna(subset=['x']), df.dropna(subset=['x']))
        self.assert_eq(ddf.dropna(subset=['y', 'z']), df.dropna(subset=['y', 'z']))
        self.assert_eq(ddf.dropna(subset=['y', 'z'], how='all'),
                       df.dropna(subset=['y', 'z'], how='all'))

        self.assert_eq(ddf.dropna(thresh=2), df.dropna(thresh=2))
        self.assert_eq(ddf.dropna(thresh=1, subset=['y', 'z']),
                       df.dropna(thresh=1, subset=['y', 'z']))

        ddf2 = ddf.copy()
        x = ddf2.x
        x.dropna(inplace=True)
        self.assert_eq(x, df.x.dropna())
        ddf2.dropna(inplace=True)
        self.assert_eq(ddf2, df.dropna())

        msg = "dropna currently only works for axis=0 or axis='index'"
        with self.assertRaisesRegex(NotImplementedError, msg):
            ddf.dropna(axis=1)
        with self.assertRaisesRegex(NotImplementedError, msg):
            ddf.dropna(axis='column')
        with self.assertRaisesRegex(NotImplementedError, msg):
            ddf.dropna(axis='foo')

    def test_value_counts(self):
        df = pd.DataFrame({'x': [1, 2, 1, 3, 3, np.nan, 1, 4]})
        ddf = koalas.from_pandas(df)

        exp = df.x.value_counts()
        res = ddf.x.value_counts()
        self.assertEqual(res.name, exp.name)
        self.assertPandasAlmostEqual(res.toPandas(), exp)

        self.assertPandasAlmostEqual(ddf.x.value_counts(normalize=True).toPandas(),
                                     df.x.value_counts(normalize=True))
        self.assertPandasAlmostEqual(ddf.x.value_counts(ascending=True).toPandas(),
                                     df.x.value_counts(ascending=True))
        self.assertPandasAlmostEqual(ddf.x.value_counts(normalize=True, dropna=False).toPandas(),
                                     df.x.value_counts(normalize=True, dropna=False))
        self.assertPandasAlmostEqual(ddf.x.value_counts(ascending=True, dropna=False).toPandas(),
                                     df.x.value_counts(ascending=True, dropna=False))

        with self.assertRaisesRegex(NotImplementedError,
                                    "value_counts currently does not support bins"):
            ddf.x.value_counts(bins=3)

        s = df.x
        s.name = 'index'
        ds = ddf.x
        ds.name = 'index'
        self.assertPandasAlmostEqual(ds.value_counts().toPandas(), s.value_counts())

    def test_isnull(self):
        df = pd.DataFrame({'x': [1, 2, 3, 4, None, 6], 'y': list('abdabd')},
                          index=[10, 20, 30, 40, 50, 60])
        a = koalas.from_pandas(df)

        self.assert_eq(a.x.notnull(), df.x.notnull())
        self.assert_eq(a.x.isnull(), df.x.isnull())
        self.assert_eq(a.notnull(), df.notnull())
        self.assert_eq(a.isnull(), df.isnull())

    def test_to_datetime(self):
        df = pd.DataFrame({'year': [2015, 2016],
                           'month': [2, 3],
                           'day': [4, 5]})
        ddf = koalas.from_pandas(df)

        self.assert_eq(pd.to_datetime(df), koalas.to_datetime(ddf))

        s = pd.Series(['3/11/2000', '3/12/2000', '3/13/2000'] * 100)
        ds = koalas.from_pandas(s)

        self.assert_eq(pd.to_datetime(s, infer_datetime_format=True),
                       koalas.to_datetime(ds, infer_datetime_format=True))

    def test_abs(self):
        df = pd.DataFrame({'A': [1, -2, 3, -4, 5],
                           'B': [1., -2, 3, -4, 5],
                           'C': [-6., -7, -8, -9, 10],
                           'D': ['a', 'b', 'c', 'd', 'e']})
        ddf = koalas.from_pandas(df)
        self.assert_eq(ddf.A.abs(), df.A.abs())
        self.assert_eq(ddf.B.abs(), df.B.abs())
        self.assert_eq(ddf[['B', 'C']].abs(), df[['B', 'C']].abs())
        # self.assert_eq(ddf.select('A', 'B').abs(), df[['A', 'B']].abs())

    def test_missing(self):
        d = self.df

        missing_functions = inspect.getmembers(_MissingPandasLikeDataFrame, inspect.isfunction)
        for name, _ in missing_functions:
            with self.assertRaisesRegex(PandasNotImplementedError,
                                        "DataFrame.*{}.*not implemented".format(name)):
                getattr(d, name)()

        missing_functions = inspect.getmembers(_MissingPandasLikeSeries, inspect.isfunction)
        for name, _ in missing_functions:
            with self.assertRaisesRegex(PandasNotImplementedError,
                                        "Series.*{}.*not implemented".format(name)):
                getattr(d.a, name)()


if __name__ == "__main__":
    try:
        import xmlrunner
        testRunner = xmlrunner.XMLTestRunner(output='target/test-reports')
    except ImportError:
        testRunner = None
    unittest.main(testRunner=testRunner, verbosity=2)
