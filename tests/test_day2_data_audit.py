"""Guard against false identities from serialized handles and false EOL crossings."""
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from src.day2_data_audit import decode_dataset_string, first_crossing, protocol_key


class AuditTests(unittest.TestCase):
    def make_string_file(self, path, text, claimed_length=None):
        with h5py.File(path, 'w') as f:
            f.create_dataset('metadata', data=np.zeros(1, dtype=np.uint8))
            encoded=text.encode('utf-16-le')
            padded=encoded + b'\0' * ((-len(encoded)) % 8)
            n=len(encoded)//2 if claimed_length is None else claimed_length
            packed=np.concatenate([np.array([1,2,1,1,n],dtype='<u8'),np.frombuffer(padded,dtype='<u8')])
            data=f.create_dataset('packed', data=packed)
            m=f.create_dataset('#subsystem#/MCOS',(1,3),dtype=h5py.ref_dtype)
            m[0,:]=[f['metadata'].ref,f['metadata'].ref,data.ref]
            handle=f.create_dataset('handle',data=np.array([3707764736,2,1,1,1,1],dtype=np.uint32))
            handle.attrs['MATLAB_class']=np.bytes_('string')

    def test_equal_handles_can_encode_different_barcodes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[Path(directory)/'a.h5',Path(directory)/'b.h5']
            texts=['EL150800460514','EL150800737291']
            for path,text in zip(paths,texts):self.make_string_file(path,text)
            with h5py.File(paths[0]) as a,h5py.File(paths[1]) as b:
                np.testing.assert_array_equal(a['handle'][()],b['handle'][()])
                self.assertEqual(decode_dataset_string(a,a['handle']),texts[0])
                self.assertEqual(decode_dataset_string(b,b['handle']),texts[1])
                self.assertNotEqual(decode_dataset_string(a,a['handle']),decode_dataset_string(b,b['handle']))

    def test_corrupt_string_length_fails_instead_of_silent_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'a.h5';self.make_string_file(path,'EL123',claimed_length=100)
            with h5py.File(path) as f:
                with self.assertRaisesRegex(ValueError,'Truncated'):decode_dataset_string(f,f['handle'])

    def test_zero_and_nonfinite_capacity_are_not_eol_crossings(self):
        frame=pd.DataFrame({'cycle':[1.,2.,3.,4.,5.],'QD':[0.,np.nan,1.1,.9,.88]})
        self.assertEqual(first_crossing(frame,.88),5.)
        self.assertTrue(np.isnan(first_crossing(frame.iloc[:4],.88)))

    def test_protocol_structure_suffix_is_preserved(self):
        self.assertEqual(protocol_key(' 4.8C(80%) -4.8C '),'4.8C(80%)-4.8C')
        self.assertNotEqual(protocol_key('4.8C(80%)-4.8C'),protocol_key('4.8C(80%)-4.8C-newstructure'))


if __name__ == '__main__':
    unittest.main()
