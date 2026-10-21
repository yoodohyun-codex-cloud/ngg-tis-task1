"""Synthetic native ABI fixtures only; no actual field bundle is consumed."""
import copy
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_lower_carrier_native as r

RECONSTRUCTION='half_face_flux; top contact term averaged over full cell face h^2'
GATES=('max_residual','max_power_error','max_current_error','max_area_relative_error',
       'max_interface_normal_current_relative_error')
EPS0=8.8541878128e-12


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n')


def write_array(folder,name,frequency,array):
    with gzip.open(Path(folder)/f'{name}-{frequency}.bin.gz','wb')as stream:
        stream.write(np.asarray(array,dtype='<c16').tobytes(order='C'))


def make_fixture(root,frequencies):
    folder=Path(root)/'basis';folder.mkdir()
    h=.625;face=(h/1000)**2;rows=[]
    centres=((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))
    for pad,(x,y)in enumerate(centres):
        cx,cy=round((x+25)/h),round((y+25)/h)
        rows.extend((pad,i,j,face)for j in range(cy-12,cy+12)for i in range(cx-12,cx+12))
    mask=Path(root)/'mask.csv'
    with mask.open('w',newline='')as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
        writer.writerows((p,i,j,format(area,'.17g'))for p,i,j,area in rows)
    properties=dict(h_mm=str(h),channels='2',frequencies=','.join(map(str,frequencies)),
        **{'validation.sc_cells':'2','validation.max_cells':'800000','bulk.counts':'14,14,40',
           'mask.path':str(mask),'mask.sha256':sha(mask)})
    tissues=(('sc',.0002,110000.),('dermis',.2,10000.),('fat',.04,1000.),('muscle',.3,100000.))
    for layer,sigma,epsilon in tissues:
        properties[layer+'.sigma']=str(sigma);properties[layer+'.epsilon_r']=str(epsilon)
    for f in frequencies:
        properties[f'z.{f}.re']='0.00004';properties[f'z.{f}.im']='-0.00009'
    for pad,(x,y)in enumerate(centres):
        properties.update({f'pad.{pad}.represented_area_m2':'0.000225',f'pad.{pad}.shape':'rectangle',
            f'pad.{pad}.width_mm':'15',f'pad.{pad}.height_mm':'15',f'pad.{pad}.rotation_deg':'0',
            f'pad.{pad}.analytic_area_mm2':'225',f'pad.{pad}.x_mm':str(x),f'pad.{pad}.y_mm':str(y)})
    config=Path(root)/'case.properties';config.write_text(''.join(k+'='+v+'\n'for k,v in properties.items()))
    boundaries=[0.,.1,5.1,10.1,25.1];counts=[2,14,14,40];faces=[0.]
    for start,stop,count in zip(boundaries,boundaries[1:],counts):
        faces.extend(start+(stop-start)*i/count for i in range(1,count+1))
    depths=[start+(stop-start)/(2*count)for start,stop,count in zip(boundaries,boundaries[1:],counts)]
    grid=folder/'grid.csv'
    with grid.open('w',newline='')as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['x_mm','y_mm','z_mm','layer','volume_m3'])
        for layer,z in enumerate(depths):
            dz=(boundaries[layer+1]-boundaries[layer])/counts[layer]/1000
            writer.writerow([0.,0.,format(z,'.17g'),layer,format(face*dz,'.17g')])
    metadata=dict(exporter_class='CloudFrequencyBasis',exporter_kind='frequency_native',
        numerical_base_class='SelectivityShapeBasis.ShapeNet',config_sha256=sha(config),
        channels=2,n_outputs=2,n_pads=4,pad_node_ids=[0,1,-1,-1],n_return_nodes=1,
        return_topology='common_GND',source_peak_V=.5,source_resistance_ohm=50.,
        phasor_convention='peak,+jomega_t',field_reconstruction=RECONSTRUCTION,
        basis_normalization=dict(source_peak_V=.5,source_Vpp=1.,source_resistance_ohm=50.,phasor_exponent='+jomega_t'),
        frequencies_Hz=list(frequencies),actual_basis_RHS_solves=2*len(frequencies),
        potential_export_basis_vectors=2*len(frequencies),extra_potential_export_solves=0,
        radius_mm=25.,total_depth_mm=25.1,
        h_xy_mm=h,sc_cells=2,bulk_layer_counts=[14,14,40],tissue_boundaries_mm=boundaries,
        z_faces_mm=faces,cells=4,nx=80)
    validation=dict.fromkeys(GATES,0.)
    validation.update(channels=2,n_outputs=2,n_pads=4,cells=4,h_xy_mm=h,sc_cells=2,
        actual_basis_RHS_solves=2*len(frequencies),extra_potential_export_solves=0)
    write_json(folder/'mesh-metadata.json',metadata);write_json(folder/'validation.json',validation)
    write_json(folder/'basis-progress.json',dict(schema='task1-frequency-basis-progress-v1',status='complete',
        requested_basis_RHS_solves=2*len(frequencies),completed_basis_RHS_solves=2*len(frequencies),
        last_frequency_Hz=frequencies[-1],last_basis_channel=1,extra_potential_export_solves=0))
    write_json(folder/'runtime-wrapper.json',dict(runtime_wrapper_class='CloudFrequencyBasis',
        numerical_base_class='SelectivityShapeBasis.ShapeNet',numerical_operator_modified=False,
        dynamic_frequency_extension=True,original_sources_modified=False))
    (folder/'BASIS_COMPLETE').touch()
    field=np.zeros((2,4,3),dtype='<c16');potential=np.zeros((2,4),dtype='<c16')
    source=np.eye(2,dtype='<c16')*.001
    loss=np.zeros((6,2,2),dtype='<c16');loss[0]=.25*source
    density=np.zeros((2,len(rows)),dtype='<c16')
    for column,(pad,_,_,_)in enumerate(rows):
        if pad==0:density[0,column]=.001/.000225
        elif pad==1:density[1,column]=.001/.000225
        elif pad==2:density[0,column]=-.001/.000225
        else:density[1,column]=-.001/.000225
    for f in frequencies:
        with (folder/f'contacts-{f}.csv').open('w',newline='')as stream:
            writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','x_mm','y_mm','area_m2'])
            writer.writerows((p,format(-25+(i+.5)*h,'.17g'),format(-25+(j+.5)*h,'.17g'),format(a,'.17g'))
                             for p,i,j,a in rows)
        for name,array in (('field',field),('potential',potential),('density',density),('source',source),('loss',loss)):
            write_array(folder,name,f,array)
    case=dict(id='synthetic-frequency-native',config_file=str(config),config_sha256=sha(config),
        mask_file=str(mask),mask_sha256=sha(mask),exporter_class='CloudFrequencyBasis',
        java_class='CloudFrequencyBasis',postprocessor='frequency_native',channels=2,n_outputs=2,n_pads=4,
        pad_node_ids=[0,1,-1,-1],n_return_nodes=1,frequencies_Hz=list(frequencies),
        expected_pad_areas_m2=[.000225]*4,h_xy_mm=h,sc_cells=2,bulk_counts=[14,14,40],cells=4,
        design=dict(channels=2,total_pads=4,source_outputs=2),
        volume_metadata=dict(h_xy_mm=h,sc_cells=2,bulk_layer_counts=[14,14,40],layer_counts=[2,14,14,40],
            radius_mm=25.,geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001))
    return dict(folder=folder,case=case,metadata=metadata,validation=validation,rows=rows,
                density=density,source=source,loss=loss,field=field,potential=potential)


class LowerCarrierNativeTests(unittest.TestCase):
    def load(self,fixture):
        return r.load_basis(fixture['folder'],fixture['case'],time.monotonic()+120.)

    def test_allowed_bundles_load_exact_shapes_and_use_actual_frequency_gamma(self):
        for frequencies in ((3000,3030),(1000,1030,2000,2030)):
            with tempfile.TemporaryDirectory()as temporary:
                fixture=make_fixture(temporary,frequencies);basis=self.load(fixture)
                self.assertEqual(set(frequencies),set(basis['f']))
                for f in frequencies:
                    self.assertEqual((2,4,3),basis['f'][f]['field'].shape)
                    self.assertEqual((2,4),basis['f'][f]['potential'].shape)
                    self.assertEqual((2,2304),basis['f'][f]['density'].shape)
                geometry,volume=r.geometry(basis,fixture['case'])
                self.assertEqual(set(frequencies),set(geometry['gamma_S_m']))
                for f in frequencies:
                    self.assertAlmostEqual(.0002,geometry['gamma_S_m'][f][0].real)
                    self.assertAlmostEqual(2*math.pi*f*EPS0*110000,geometry['gamma_S_m'][f][0].imag,places=13)

    def test_wrong_exporter_bundle_topology_or_unreported_additional_solves_are_rejected(self):
        mutations=(lambda m:m.update(exporter_class='SelectivityShapeBasis'),
                   lambda m:m.update(exporter_kind='grouped_native'),
                   lambda m:m.update(frequencies_Hz=[1000,1010]),
                   lambda m:m.update(extra_potential_export_solves=1),
                   lambda m:m.update(actual_basis_RHS_solves=5),
                   lambda m:m.update(pad_node_ids=[0,1,0,-1]))
        for mutate in mutations:
            with tempfile.TemporaryDirectory()as temporary:
                fixture=make_fixture(temporary,(3000,3030));metadata=copy.deepcopy(fixture['metadata'])
                mutate(metadata);write_json(fixture['folder']/'mesh-metadata.json',metadata)
                with self.assertRaises(ValueError):self.load(fixture)

    def test_missing_native_metadata_or_spectral_line_never_uses_a_substitute(self):
        for name in ('mesh-metadata.json','potential-3030.bin.gz'):
            with tempfile.TemporaryDirectory()as temporary:
                fixture=make_fixture(temporary,(3000,3030));(fixture['folder']/name).unlink()
                with self.assertRaises((ValueError,FileNotFoundError)):self.load(fixture)

    def test_complex_loss_must_be_hermitian_and_conserve_arbitrary_output_power(self):
        for kind in ('nonhermitian','power'):
            with tempfile.TemporaryDirectory()as temporary:
                fixture=make_fixture(temporary,(3000,3030));loss=fixture['loss'].copy()
                if kind=='nonhermitian':loss[0,0,1]=1e-6j
                else:loss[0]*=1.01
                write_array(fixture['folder'],'loss',3000,loss)
                with self.assertRaises(ValueError):self.load(fixture)

    def test_common_gnd_checks_coherent_sum_without_exclusive_return_pair_assumption(self):
        with tempfile.TemporaryDirectory()as temporary:
            fixture=make_fixture(temporary,(3000,3030));density=fixture['density'].copy()
            returns=np.array([pad>=2 for pad,_,_,_ in fixture['rows']])
            density[:,returns]=-.001/(2*.000225)
            for f in (3000,3030):write_array(fixture['folder'],'density',f,density)
            basis=self.load(fixture)
            self.assertEqual(2,len(basis['f']))
            bad=density.copy();bad[0,returns]*=-1
            write_array(fixture['folder'],'density',3000,bad)
            with self.assertRaises(ValueError):self.load(fixture)

    def test_truncated_oversized_nonfinite_and_invalid_gzip_arrays_are_rejected(self):
        for kind in ('truncated','oversized','nonfinite','gzip'):
            with tempfile.TemporaryDirectory()as temporary:
                fixture=make_fixture(temporary,(3000,3030));path=fixture['folder']/'field-3000.bin.gz'
                raw=fixture['field'].tobytes()
                if kind=='gzip':path.write_bytes(b'not a gzip stream')
                elif kind=='nonfinite':
                    field=fixture['field'].copy();field[0,0,0]=np.nan
                    write_array(fixture['folder'],'field',3000,field)
                else:
                    with gzip.open(path,'wb')as stream:stream.write(raw[:-16]if kind=='truncated'else raw+b'X')
                with self.assertRaises((ValueError,EOFError,OSError)):self.load(fixture)

    def test_legacy_exporter_is_only_a_regression_reference_with_all_ten_array_gates(self):
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);newroot=root/'new';newroot.mkdir()
            new=make_fixture(newroot,(3000,3030));basis=self.load(new)
            run=root/'old-run';oldroot=run/'bases';oldroot.mkdir(parents=True)
            old=make_fixture(oldroot,(3000,3030,9000,9090))
            legacy=copy.deepcopy(old['metadata']);legacy['exporter_class']='SelectivityShapeBasis'
            legacy.pop('exporter_kind');write_json(old['folder']/'mesh-metadata.json',legacy)
            oldcase=copy.deepcopy(old['case']);oldcase['id']=old['folder'].name
            oldcase['exporter_class']='SelectivityShapeBasis';oldcase['java_class']='CloudShapeBasis'
            write_json(run/'preregistration.json',dict(cases=[oldcase]))
            (run/'cases').mkdir();(run/'postprocess').mkdir()
            summary=run/'postprocess'/'summary.json';write_json(summary,dict(status='complete'))
            write_json(run/'cases'/(oldcase['id']+'.json'),dict(status='complete',validation=old['validation'],
                postprocess_path=str(summary),postprocess_sha256=sha(summary)))
            with self.assertRaises(ValueError):
                r.load_basis(old['folder'],oldcase,time.monotonic()+120.)
            report=r.strict_regression_compare(basis,old['folder'],time.monotonic()+120.)
            self.assertEqual('passed',report['status']);self.assertEqual(10,len(report['comparisons']))
            self.assertTrue(all(row['passed']and row['decoded_binary_byte_equal']for row in report['comparisons']))
            self.assertTrue(report['legacy_exporter_accepted_only_as_reference'])
            changed=copy.deepcopy(basis)
            changed['f'][3000]['field']=basis['f'][3000]['field'].copy()
            changed['f'][3000]['field'][0,0,0]=2e-12
            report=r.strict_regression_compare(changed,old['folder'],time.monotonic()+120.)
            self.assertEqual('failed',report['status'])
            failures=[row for row in report['comparisons']if not row['passed']]
            self.assertEqual(1,len(failures));self.assertEqual('field',failures[0]['array_kind'])
            self.assertEqual(1,failures[0]['failed_component_count'])


if __name__=='__main__':
    unittest.main()
