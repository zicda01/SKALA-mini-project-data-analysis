"""Check rejection of stale sources and target-independent, group-safe splits."""
import unittest
import numpy as np
import pandas as pd
from src.day2_dataset import build_cell_table, assign_splits, BATCH1_UNCERTAIN_IDS


class DatasetTests(unittest.TestCase):
    def setUp(self):
        rows=[]
        for batch,n in [('batch1',40),('batch2',8),('batch3',4)]:
            for i in range(n):
                rows.append({'batch':batch,'cell_id':i,'cycle_life':500.+i,'charging_policy':f'p{i//2}',
                             'barcode_key':f'{batch}-{i}','channel_id_decoded':str(i),'protocol_key':f'p{i//2}'})
        self.audit=pd.DataFrame(rows)
        self.gallery=self.audit[['batch','cell_id','cycle_life']].copy()
        for key,value in dict(deltaQ_var=.001,deltaQ_min=-.05,deltaQ_status='accepted',
                              peak_positive_I_cycle10=4.,early_observed_rows=91).items():self.gallery[key]=value
        self.quality=self.audit[['batch','cell_id','cycle_life','charging_policy']].copy()
        for key,value in dict(QD_slope_masked=-.00001,QD_slope_retained=-.00002,n_QD_masked=91,
                              n_QD_retained=91,early_high_QD_rows=0).items():self.quality[key]=value

    def build(self):return build_cell_table(self.gallery,self.quality,self.audit)

    def test_stale_target_or_partial_sources_fail(self):
        self.gallery.loc[0,'cycle_life']+=1
        with self.assertRaisesRegex(ValueError,'lifetime labels disagree'):self.build()
        self.gallery.loc[0,'cycle_life']-=1
        self.gallery=self.gallery.iloc[1:]
        with self.assertRaisesRegex(ValueError,'different cell coverage'):self.build()

    def test_exclusions_and_unscaled_values_preserve_original_targets(self):
        self.audit.loc[40,'cycle_life']=np.nan
        self.gallery.loc[40,'cycle_life']=np.nan
        self.quality.loc[40,'cycle_life']=np.nan
        t=self.build()
        b1=t[t.batch.eq('batch1')]
        self.assertEqual(set(b1.loc[~b1.cohort_eligible,'cell_id']),BATCH1_UNCERTAIN_IDS)
        self.assertEqual(t.iloc[40].exclusion_reason,'missing_or_invalid_lifetime_label')
        np.testing.assert_allclose(t.log10_deltaQ_var,-3.)
        np.testing.assert_allclose(t.QD_slope_masked,-.00001)
        np.testing.assert_allclose(t.cycle_life,self.audit.cycle_life,equal_nan=True)
        self.assertNotIn('last_positive_QD',t.columns)

    def test_split_is_target_independent_order_invariant_and_group_safe(self):
        t=self.build();a,m,_=assign_splits(t)
        shuffled=t.sample(frac=1,random_state=7).copy()
        shuffled['cycle_life']=shuffled.cycle_life * 10
        b,_,_=assign_splits(shuffled)
        pd.testing.assert_frame_equal(a[['batch','cell_id','partition','cv_valid_fold']],b[['batch','cell_id','partition','cv_valid_fold']])
        dev=a[a.partition.eq('development')];hold=a[a.partition.eq('holdout')]
        self.assertFalse(set(dev.protocol_key)&set(hold.protocol_key))
        self.assertTrue(a.loc[~a.partition.eq('development'),'cv_valid_fold'].isna().all())
        for fold,g in m.groupby('fold'):
            tr=g[g.role.eq('train')];va=g[g.role.eq('valid')]
            self.assertFalse(set(tr.protocol_key)&set(va.protocol_key))
            self.assertEqual(set(g.cell_id),set(dev.cell_id))
        self.assertEqual(len(m[m.role.eq('valid')]),len(dev))


if __name__=='__main__':unittest.main()
