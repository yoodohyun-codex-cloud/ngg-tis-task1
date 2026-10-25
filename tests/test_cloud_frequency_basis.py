"""Compile and exercise only tiny analytic/guard fixtures; no phantom solve."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'tools/java/CloudFrequencyBasis.java'


class CloudFrequencyBasisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='task1-frequency-java-fixtures-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.classes = Path(cls.tmp.name)/'classes';cls.classes.mkdir()
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        javac=shutil.which('javac') or '/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/javac'
        cls.java=str(Path(javac).resolve().parent/'java')
        subprocess.run([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(cls.classes),
            *map(str,[ROOT/'tis-java/TisSweep.java',ROOT/'tis-java/ExploreBasis.java',ROOT/'tis-java/SelectivityShapeBasis.java',
                      ROOT/'tools/java/CloudShapeBasis.java',SOURCE])],check=True,capture_output=True,text=True,timeout=60)

    def command(self,*args):
        return subprocess.run([self.java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1',
            '-cp',str(self.classes),'CloudFrequencyBasis',*args],capture_output=True,text=True,timeout=60)

    def test_actual_frequency_analytic_restrictions_and_dynamic_metadata(self):
        result=self.command('--selftest')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('actual1k/1030/2k/2030/3k/3030',result.stdout)
        self.assertIn('phantom PDE0',result.stdout)

    def test_nonregistered_direct_parent_cannot_create_native_output(self):
        root=Path(self.tmp.name);config=root/'fixture.properties';config.write_text('channels=2\nfrequencies=3000,3030\n')
        output=root/'must-not-exist'
        ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        result=self.command('--execute-parent',str(os.getpid()),ticks,str(config),str(output))
        self.assertNotEqual(result.returncode,0)
        self.assertIn('task1_lower_carrier.py --execute --output run',result.stderr)
        self.assertFalse(output.exists())

    def test_bulk_solver_and_reconstruction_are_inherited(self):
        text=SOURCE.read_text()
        self.assertIn('extends CloudShapeBasis',text)
        for forbidden in ('class ShapeNet','double[] solve(','double[][] field(','C[][][] lossMatrices('):
            self.assertNotIn(forbidden,text)
        old=(ROOT/'tools/java/CloudShapeBasis.java').read_text()
        for unchanged in (
            'ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),channels,Double.parseDouble(fs),patches);',
            'C[][][] q=net.lossMatrices(volts);',
            'new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02)',
            'net.edgeCurrent(c.edge,volts[a]).scale(-1/c.edge.area)',
            'worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7'):
            self.assertIn(unchanged,old);self.assertIn(unchanged,text)


if __name__=='__main__':unittest.main()
