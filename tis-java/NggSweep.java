import java.io.*;
import java.util.*;

/** Uses the established FVM solver with measured-minus-Rs electrode boundaries.
 * Writes separate run folders. The historical results/ files are not overwritten.
 */
public class NggSweep extends TisSweep {
  static class MeasuredScenario extends Scenario {
    C z1,z2;
    MeasuredScenario(String name, Properties p, double rs, double sc) {
      super(name,1,0,sc);
      double area=number(p,"measurement.area_m2");
      if(!(area>0))throw new IllegalArgumentException("Invalid measured area");
      z1=new C(number(p,"measured.2000.real_ohm")-rs,number(p,"measured.2000.imag_ohm")).scale(area);
      z2=new C(number(p,"measured.2010.real_ohm")-rs,number(p,"measured.2010.imag_ohm")).scale(area);
      if(z1.r<0||z2.r<0||!Double.isFinite(z1.abs())||!Double.isFinite(z2.abs()))throw new IllegalArgumentException("Invalid passive electrode boundary");
    }
    C zc(double w) {
      double f=w/(2*Math.PI);
      if(Math.abs(f-2000)<1e-6)return z1;
      if(Math.abs(f-2010)<1e-6)return z2;
      throw new IllegalArgumentException("Measured boundary supports only 2000 and 2010 Hz");
    }
  }
  static double number(Properties p,String key) {
    String value=p.getProperty(key);if(value==null)throw new IllegalArgumentException("Missing "+key);
    double v=Double.parseDouble(value);if(!Double.isFinite(v))throw new IllegalArgumentException(key);return v;
  }
  static Properties readProperties(String name)throws Exception {
    Properties p=new Properties();InputStream in=new FileInputStream(name);try{p.load(in);}finally{in.close();}return p;
  }
  static void validate(Result r) {
    if(!Double.isFinite(r.target)||r.target<0||r.res>2e-7||r.powerError>2e-7)throw new RuntimeException("Invalid solve");
    for(double[] m:new double[][]{r.m1,r.m2}){
      double balance=m[7]/Math.max(Math.hypot(m[0],m[1])*Math.sqrt(2),1e-20);
      if(balance>2e-6)throw new RuntimeException("Electrode current balance: "+balance);
      double loss=0;for(int i=9;i<14;i++)loss+=m[i];
      if(Math.abs(loss-m[5])/Math.max(m[5],1e-20)>1e-7)throw new RuntimeException("Layer power partition");
    }
  }
  static final String HEADER="scenario,layout,h_mm,target20_V_m,center12_55_V_m,global_sampled_V_m,max_x_mm,max_y_mm,max_z_mm,I_CH1_source_RMS_A,I_CH2_source_RMS_A,max_surface_J_RMS_upper_A_m2,tissue_contact_power_W,residual,power_balance_error,CH1_own_frequency_Vpp,CH2_own_frequency_Vpp,SC_power_W,dermis_power_W,fat_power_W,muscle_power_W,contact_power_W";
  static void row(PrintWriter out,Scenario s,Result r,double h) {
    out.printf("%s,%s,%.9g,%.12g,%.12g,%.12g,%.9g,%.9g,%.9g,%.12g,%.12g,%.12g,%.12g,%.4g,%.4g,%.12g,%.12g",s.name,r.layout.name,h,r.target,r.center,r.max,r.maxx*1000,r.maxy*1000,r.maxz*1000,Math.hypot(r.m1[0],r.m2[0]),Math.hypot(r.m1[1],r.m2[1]),Math.hypot(r.m1[4],r.m2[4]),r.m1[5]+r.m2[5],r.res,r.powerError,r.m1[8],r.m2[8]);
    for(int i=9;i<14;i++)out.printf(",%.12g",r.m1[i]+r.m2[i]);out.println();out.flush();
  }
  public static void main(String[] args)throws Exception {
    Locale.setDefault(Locale.US);
    selftest();
    Properties p=readProperties("electrode-data/bare-ngg-initial.properties");
    MeasuredScenario test=new MeasuredScenario("test",p,number(p,"fit.Rs_ohm"),1);
    double expected=(number(p,"measured.2000.real_ohm")-number(p,"fit.Rs_ohm"))*number(p,"measurement.area_m2");
    if(Math.abs(test.zc(2*Math.PI*2000).r-expected)>1e-14)throw new RuntimeException("Area scaling");
    if(args.length==1&&args[0].equals("--selftest")){System.out.println("Measured impedance area/frequency checks passed");return;}
    if(args.length!=1)throw new IllegalArgumentException("Usage: NggSweep <new-output-directory>");
    File folder=new File(args[0]);if(folder.exists())throw new IllegalArgumentException("Output already exists");
    if(!new File(folder,"fields").mkdirs())throw new IOException("Cannot create output folder");
    Properties cfg=readProperties("simulation.properties");String[] layers={"sc","dermis","fat","muscle"};
    for(int k=0;k<4;k++){SIG[k]=number(cfg,layers[k]+".sigma");ER[k]=number(cfg,layers[k]+".epsilon_r");if(SIG[k]<=0||ER[k]<0)throw new IllegalArgumentException("Invalid tissue properties");}
    double rs=number(p,"fit.Rs_ohm");
    Scenario[] scenarios={new Scenario("legacy_rc",.01,.001,1),new MeasuredScenario("ngg_initial",p,rs,1),
      new MeasuredScenario("rs_low",p,number(p,"fit.Rs_low_ohm"),1),new MeasuredScenario("rs_high",p,number(p,"fit.Rs_high_ohm"),1),
      new MeasuredScenario("sc_low",p,rs,.1),new MeasuredScenario("sc_high",p,rs,10)};
    List<Layout> layouts=layouts();Mesh coarse=new Mesh(2.5);
    PrintWriter out=new PrintWriter(new File(folder,"sweep.csv"),"UTF-8");out.println(HEADER);
    PrintWriter refined=new PrintWriter(new File(folder,"refined-summary.csv"),"UTF-8");refined.println(HEADER);
    PrintWriter pos=new PrintWriter(new File(folder,"layouts.csv"),"UTF-8");pos.println("layout,electrode,x_mm,y_mm");
    for(Layout l:layouts)for(int e=0;e<4;e++)pos.printf("%s,%s,%.9g,%.9g%n",l.name,new String[]{"CH1_plus","CH2_plus","GND_A","GND_B"}[e],l.xy[e][0]*1000,l.xy[e][1]*1000);pos.close();
    int done=0;
    for(int si=0;si<scenarios.length;si++){
      Scenario scenario=scenarios[si];Result best=null,center=null;
      for(Layout layout:layouts){
        Result r=run(coarse,scenario,layout,si<2);validate(r);row(out,scenario,r,2.5);
        if(si<2)export(r,new File(folder,"fields/"+scenario.name+"__"+layout.name+"__coarse").getPath());
        if(best==null||r.target>best.target)best=r;if(center==null||r.center>center.center)center=r;
        System.out.printf("SOLVE %d/54 %s %s target=%.6f residual=%.2g%n",++done,scenario.name,layout.name,r.target,r.res);
      }
      if(si<2){
        Set<String> names=new LinkedHashSet<String>();names.add(best.layout.name);names.add(center.layout.name);
        for(String name:names){Layout chosen=null;for(Layout l:layouts)if(l.name.equals(name))chosen=l;
          Result r=run(new Mesh(1.25),scenario,chosen,true);validate(r);row(refined,scenario,r,1.25);
          export(r,new File(folder,"fields/"+scenario.name+"__"+name+"__fine").getPath());
          System.out.printf("REFINED %s %s target=%.9f%n",scenario.name,name,r.target);
        }
      }
    }
    out.close();refined.close();
    PrintWriter success=new PrintWriter(new File(folder,"SOLVER_COMPLETE.txt"),"UTF-8");success.println("54 coarse cases; legacy and NGG target/center winners refined. Residual, current and power balance checks passed.");success.close();
  }
}
