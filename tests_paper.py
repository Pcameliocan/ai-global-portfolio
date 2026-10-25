import unittest
from paper_engine import fill_pending, value_portfolio, target_weights

class TestPaper(unittest.TestCase):
    def test_no_same_day_fill(self):
        s={'cash':5000,'holdings':{},'pending':{'signal_date':'2026-10-20','weights':{'MSFT':.20}}}
        cash,h,t,p=fill_pending(s,{'MSFT':100},'2026-10-20')
        self.assertEqual(cash,5000)
        self.assertEqual(t,[])
        self.assertIsNotNone(p)
    def test_next_day_and_fee_and_cash_floor(self):
        s={'cash':5000,'holdings':{},'pending':{'signal_date':'2026-10-20','weights':{'MSFT':.20,'NVDA':.20}}}
        cash,h,t,p=fill_pending(s,{'MSFT':100,'NVDA':200},'2026-10-21')
        self.assertAlmostEqual(cash,2998,places=4)
        self.assertAlmostEqual(value_portfolio(cash,h,{'MSFT':100,'NVDA':200}),4998,places=2)
        self.assertEqual(len(t),2)
        self.assertIsNone(p)
    def test_bad_target_rejected(self):
        s={'cash':5000,'holdings':{},'pending':{'signal_date':'2026-10-20','weights':{'MSFT':.9}}}
        with self.assertRaises(ValueError):fill_pending(s,{'MSFT':100},'2026-10-21')
    def test_missing_quote_aborts(self):
        s={'cash':5000,'holdings':{'MSFT':2},'pending':{'signal_date':'2026-10-20','weights':{}}}
        with self.assertRaises(ValueError):fill_pending(s,{},'2026-10-21')
    def test_target_weights(self):
        self.assertEqual(target_weights([{'Símbolo':'MSFT','Peso %':20}]),{'MSFT':.2})

if __name__=='__main__':unittest.main()
