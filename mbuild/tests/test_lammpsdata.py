import numpy as np
import pytest

import mbuild as mb
from mbuild.tests.base_test import BaseTest
from mbuild.utils.io import get_fn
from mbuild.formats.lammpsdata import write_lammpsdata
from mbuild.utils.io import has_foyer


@pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
class TestLammpsData(BaseTest):

    def test_save(self, ethane):
        ethane.save(filename='ethane.lammps')

    def test_save_forcefield(self, ethane):
        ethane.save(filename='ethane-opls.lammps', forcefield_name='oplsaa')

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    def test_save_charmm(self):
        cmpd = mb.load(get_fn('charmm_dihedral.mol2'))
        for i in cmpd.particles():
            i.name = "_{}".format(i.name)
        structure = cmpd.to_parmed(box=cmpd.boundingbox, 
                                    residues=set([p.parent.name for \
                                                 p in cmpd.particles()]))

        from foyer import Forcefield
        ff = Forcefield(forcefield_files=[get_fn('charmm_truncated.xml')])
        structure = ff.apply(structure, assert_dihedral_params=False)

        from mbuild.formats.lammpsdata import write_lammpsdata
        write_lammpsdata(structure, 'charmm_dihedral.lammps')
        out_lammps = open('charmm_dihedral.lammps', 'r').readlines()
        for i, line in enumerate(out_lammps):
            if 'Angle Coeffs' in line:
                assert '# charmm' in line
                assert '#\tk(kcal/mol/rad^2)\t\ttheteq(deg)\tk(kcal/mol/angstrom^2)\treq(angstrom)\n' in out_lammps[i+1]
                assert len(out_lammps[i+2].split('#')[0].split()) == 5
            elif 'Dihedral Coeffs' in line:
                assert '# charmm' in line
                assert '#k, n, phi, weight' in out_lammps[i+1]
                assert len(out_lammps[i+2].split('#')[0].split()) == 5
            else:
                pass

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    def test_save_box(self, ethane):
        box = mb.Box(lengths=np.array([2.0, 2.0, 2.0]))
        ethane.save(filename='ethane-box.lammps', forcefield_name='oplsaa', box=box)

    def test_nbfix(self, ethane):
        from foyer import Forcefield

        OPLSAA = Forcefield(name='oplsaa')
        structure = OPLSAA.apply(ethane)
        # Add nbfixes
        types = list(set([a.atom_type for a in structure.atoms]))
        types[0].add_nbfix(types[1].name, 1.2, 2.1)
        types[1].add_nbfix(types[0].name, 1.2, 2.1)
        write_lammpsdata(filename='nbfix.lammps', structure=structure)

        checked_section = False
        with open('nbfix.lammps', 'r') as fi:
            while not checked_section:
                line = fi.readline()
                if 'PairIJ Coeffs' in line:
                    fi.readline()
                    line = fi.readline().partition('#')[0]
                    assert np.allclose(
                        np.asarray(line.split(), dtype=float),
                        [1, 1, 0.066, 3.5])
                    line = fi.readline().partition('#')[0]
                    assert np.allclose(
                        np.asarray(line.split(), dtype=float),
                        [1, 2, 2.1, 1.06907846])
                    line = fi.readline().partition('#')[0]
                    assert np.allclose(
                        np.asarray(line.split(), dtype=float),
                        [2, 2, 0.03, 2.5])
                    line = fi.readline()
                    checked_section = True
                # Break if PairIJ Coeffs is not found
                if 'Atoms' in line:
                    break

    def test_save_triclinic_box(self, ethane):
        box = mb.Box(lengths=np.array([2.0, 2.0, 2.0]), angles=[60, 70, 80])
        ethane.save(filename='triclinic-box.lammps', forcefield_name='oplsaa', box=box)

    @pytest.mark.parametrize(
        'atom_style, n_columns',
        [('full', 7), ('atomic', 5), ('molecular', 6), ('charge', 6)]
    ) 
    def test_writing_atom_styles(self, ethane, atom_style, n_columns):
        ethane.save(filename='ethane.lammps', atom_style=atom_style)
        with open('ethane.lammps', 'r') as f:
            for line in f:
                if "Atoms" not in line:
                    continue
                    atoms_header = next(f)
                    first_atom_line = next(f)
                    columns = first_atom_line.split("\t")
                    assert len(columns) == n_columns
