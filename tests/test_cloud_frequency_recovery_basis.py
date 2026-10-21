"""Tiny recovery-version fixtures; no phantom PDE or original-source edits."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tools/java/CloudFrequencyRecoveryBasis.java'


class CloudFrequencyRecoveryBasisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='task1-frequency-recovery-fixtures-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.classes=Path(cls.tmp.name)/'classes';cls.classes.mkdir()
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        javac=shutil.which('javac')or'/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/javac'
        cls.java=str(Path(javac).resolve().parent/'java')
        subprocess.run([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(cls.classes),
            *map(str,[ROOT/'tis-java/TisSweep.java',ROOT/'tis-java/ExploreBasis.java',ROOT/'tis-java/SelectivityShapeBasis.java',
                      ROOT/'tools/java/CloudShapeBasis.java',SOURCE])],check=True,capture_output=True,text=True,timeout=60)

    def command(self,*args):
        return subprocess.run([self.java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(self.classes),
            'CloudFrequencyRecoveryBasis',*args],capture_output=True,text=True,timeout=60)

    def test_tiny_analytic_recovery_identity_metadata_and_no_duplicate_regression(self):
        result=self.command('--selftest')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('phantom PDE0',result.stdout)
        text=SOURCE.read_text()
        self.assertIn('new String[]{"3000,3030","1000,1030"',text)
        self.assertIn('Recovery executes only exact four lower-carrier frequencies',text)
        self.assertIn('frequency_recovery_native',text)

    def test_only_exact_recovery_parent_can_create_native_output(self):
        root=Path(self.tmp.name);config=root/'fixture.properties'
        config.write_text('channels=2\nfrequencies=1000,1030,2000,2030\n')
        output=root/'must-not-exist';ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        result=self.command('--execute-parent',str(os.getpid()),ticks,str(config),str(output))
        self.assertNotEqual(result.returncode,0)
        self.assertIn('task1_lower_carrier_recovery.py --execute --output run',result.stderr)
        self.assertFalse(output.exists())

    def test_original_numerical_export_expressions_and_dual_lock_guard_preserved(self):
        old=(ROOT/'tools/java/CloudFrequencyBasis.java').read_text();new=SOURCE.read_text()
        self.assertNotIn('class ShapeNet',new);self.assertNotIn('double[] solve(',new)
        for unchanged in (
            'ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),channels,Double.parseDouble(fs),patches);',
            'C[][][] q=net.lossMatrices(volts);',
            'new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02)',
            'owned.contains("FLOCK")&&owned.contains("POSIX")',
            'worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7'):
            self.assertIn(unchanged,old);self.assertIn(unchanged,new)


if __name__=='__main__':unittest.main()
