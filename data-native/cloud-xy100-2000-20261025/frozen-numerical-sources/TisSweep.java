import java.io.*;
import java.util.*;

/** Standalone exploratory complex finite-volume solver. SI units internally.
 * Material inputs are deliberately uncalibrated hypotheses, NOT measured phantom data.
 * Common ground, both sources enabled, 50 ohm series output resistance.
 */
public class TisSweep {
  static final double EPS0=8.8541878128e-12;
  static double[] SIG={.0002,.2,.04,.3},ER={110000,10000,1000,100000};
  static class C {
    double r,i; C(double r,double i){this.r=r;this.i=i;}
    C add(C b){return new C(r+b.r,i+b.i);} C sub(C b){return new C(r-b.r,i-b.i);}
    C mul(C b){return new C(r*b.r-i*b.i,r*b.i+i*b.r);}
    C scale(double a){return new C(r*a,i*a);} C div(C b){double d=b.r*b.r+b.i*b.i;return new C((r*b.r+i*b.i)/d,(i*b.r-r*b.i)/d);}
    double abs(){return Math.hypot(r,i);} double abs2(){return r*r+i*i;}
  }
  static class Edge {int a,b,axis; C g; double area; Edge(int a,int b,C g,int axis,double area){this.a=a;this.b=b;this.g=g;this.axis=axis;this.area=area;}}
  static class Mesh {
    int nx,nz,n; double h; int[][][] id; double[] z,dz; int[] layer,ix,iy,iz; double[] x,y;
    Mesh(double hm){
      h=hm/1000;nx=(int)Math.round(.05/h);List<Double> dd=new ArrayList<Double>(); List<Integer> ll=new ArrayList<Integer>();
      double[] thick={.0001,.005,.005,.015};
      for(int l=0;l<4;l++){int count=l==0?2:(int)Math.ceil(thick[l]/(h*.6));for(int k=0;k<count;k++){dd.add(thick[l]/count);ll.add(l);}}
      nz=dd.size();z=new double[nz];dz=new double[nz];layer=new int[nz];double zz=0;
      for(int k=0;k<nz;k++){dz[k]=dd.get(k);z[k]=zz+dz[k]/2;zz+=dz[k];layer[k]=ll.get(k);}
      id=new int[nz][nx][nx]; List<Integer> xx=new ArrayList<Integer>(),yy=new ArrayList<Integer>(),kk=new ArrayList<Integer>();
      for(int k=0;k<nz;k++)for(int j=0;j<nx;j++)for(int i=0;i<nx;i++){
        double a=-.025+(i+.5)*h,b=-.025+(j+.5)*h;id[k][j][i]=-1;
        if(a*a+b*b<.025*.025){id[k][j][i]=xx.size();xx.add(i);yy.add(j);kk.add(k);}
      }
      n=xx.size();ix=new int[n];iy=new int[n];iz=new int[n];x=new double[n];y=new double[n];
      for(int p=0;p<n;p++){ix[p]=xx.get(p);iy[p]=yy.get(p);iz[p]=kk.get(p);x[p]=-.025+(ix[p]+.5)*h;y[p]=-.025+(iy[p]+.5)*h;}
    }
    int at(int i,int j,int k){return i<0||j<0||k<0||i>=nx||j>=nx||k>=nz?-1:id[k][j][i];}
  }
  static class Scenario {
    String name;double rho,cap,scFactor;
    Scenario(String n,double r,double c,double sf){name=n;rho=r;cap=c;scFactor=sf;}
    // Area-specific parallel RC impedance: 1/(1/rho + j*w*C_area).
    C zc(double w){return new C(1,0).div(new C(1/rho,w*cap));}
  }
  static class Layout {
    String name;double[][] xy;
    Layout(String n,double[][] p){name=n;xy=p;}
  }
  static class Net {
    Mesh m;Scenario s;Layout l;int N;double omega; List<Edge> edges=new ArrayList<Edge>();C[] gamma; double[] dr,di;int[] electrode;
    Net(Mesh m,Scenario s,Layout l,double f){
      this.m=m;this.s=s;this.l=l;N=m.n+2;dr=new double[N];di=new double[N];electrode=new int[m.n];Arrays.fill(electrode,-1);
      double w=2*Math.PI*f;omega=w;double[] sig=SIG,eps=ER;gamma=new C[4];
      for(int k=0;k<4;k++)gamma[k]=new C(sig[k]*(k==0?s.scFactor:1),w*EPS0*eps[k]*(k==0?s.scFactor:1));
      for(int p=0;p<m.n;p++){
        int i=m.ix[p],j=m.iy[p],k=m.iz[p];C ga=gamma[m.layer[k]];
        int q=m.at(i+1,j,k); if(q>=0)add(p,q,ga.scale(m.dz[k]),0,m.h*m.dz[k]);
        q=m.at(i,j+1,k);if(q>=0)add(p,q,ga.scale(m.dz[k]),1,m.h*m.dz[k]);
        q=m.at(i,j,k+1);if(q>=0){C zz=new C(m.dz[k]/2,0).div(ga).add(new C(m.dz[k+1]/2,0).div(gamma[m.layer[k+1]]));add(p,q,new C(m.h*m.h,0).div(zz),2,m.h*m.h);}
        if(k==0)for(int e=0;e<4;e++)if(Math.abs(m.x[p]-l.xy[e][0])<.005-1e-10&&Math.abs(m.y[p]-l.xy[e][1])<.005-1e-10){
          if(electrode[p]>=0)throw new IllegalArgumentException("overlapping electrodes");electrode[p]=e;
          C zz=s.zc(w).add(new C(m.dz[0]/2,0).div(ga));add(p,e<2?m.n+e:-1,new C(m.h*m.h,0).div(zz),-1,m.h*m.h);
        }
      }
      for(int e=0;e<4;e++){int count=0;for(int a:electrode)if(a==e)count++;if(Math.abs(count*m.h*m.h-.0001)>1e-10)throw new IllegalArgumentException("Electrode area not represented exactly: "+count);}
      dr[m.n]+=.02;dr[m.n+1]+=.02;
    }
    void add(int a,int b,C g,int axis,double area){edges.add(new Edge(a,b,g,axis,area));dr[a]+=g.r;di[a]+=g.i;if(b>=0){dr[b]+=g.r;di[b]+=g.i;}}
    void pre(double[] x){for(int p=0;p<N;p++){double d=dr[p]*dr[p]+di[p]*di[p],a=x[2*p],b=x[2*p+1];x[2*p]=(a*dr[p]+b*di[p])/d;x[2*p+1]=(b*dr[p]-a*di[p])/d;}}
    double[] raw(double[] x){double[] a=new double[2*N];for(int p=0;p<N;p++){a[2*p]=dr[p]*x[2*p]-di[p]*x[2*p+1];a[2*p+1]=di[p]*x[2*p]+dr[p]*x[2*p+1];}for(Edge e:edges)if(e.b>=0){int p=2*e.a,q=2*e.b; a[p]-=e.g.r*x[q]-e.g.i*x[q+1];a[p+1]-=e.g.i*x[q]+e.g.r*x[q+1];a[q]-=e.g.r*x[p]-e.g.i*x[p+1];a[q+1]-=e.g.i*x[p]+e.g.r*x[p+1];}return a;}
    double[] apply(double[] x){double[] a=raw(x);pre(a);return a;}
    double residual;int iterations;
    C cdot(double[] a,double[] b){double re=0,im=0;for(int j=0;j<a.length;j+=2){re+=a[j]*b[j]-a[j+1]*b[j+1];im+=a[j]*b[j+1]+a[j+1]*b[j];}return new C(re,im);}
    void caxpy(double[] x,C c,double[] a){for(int j=0;j<x.length;j+=2){x[j]+=c.r*a[j]-c.i*a[j+1];x[j+1]+=c.r*a[j+1]+c.i*a[j];}}
    double[] solve(int source){
      int n=2*N;double[] b=new double[n];b[2*(m.n+source)]=.01;
      double[] x=new double[n],r=b.clone(),z=r.clone();pre(z);double[] p=z.clone();C rho=cdot(r,z);double norm=Math.sqrt(dot(b,b));
      for(int it=0;it<12000;it++){
        double[] ap=raw(p);C alpha=rho.div(cdot(p,ap));caxpy(x,alpha,p);caxpy(r,alpha.scale(-1),ap);
        if(Math.sqrt(dot(r,r))/norm<1e-9){iterations=it+1;break;}
        z=r.clone();pre(z);C next=cdot(r,z),beta=next.div(rho);double[] np=z.clone();caxpy(np,beta,p);p=np;rho=next;
        if(!Double.isFinite(rho.r)||it==11999)throw new RuntimeException("COCG solver failed");
      }
      double[] ax=raw(x);for(int j=0;j<n;j++)ax[j]-=b[j];residual=Math.sqrt(dot(ax,ax)/dot(b,b));if(residual>2e-7)throw new RuntimeException("Residual "+residual);return x;
    }
    C val(double[] v,int p){return p<0?new C(0,0):new C(v[2*p],v[2*p+1]);}
    double[][] field(double[] v){
      double[][] e=new double[m.n][6];
      for(Edge a:edges){C current=a.g.mul(val(v,a.a).sub(val(v,a.b)));if(a.axis>=0){
        C ea=current.div(gamma[m.layer[m.iz[a.a]]]).scale(.5/a.area); e[a.a][2*a.axis]+=ea.r;e[a.a][2*a.axis+1]+=ea.i;
        C eb=current.div(gamma[m.layer[m.iz[a.b]]]).scale(.5/a.area); e[a.b][2*a.axis]+=eb.r;e[a.b][2*a.axis+1]+=eb.i;
      }else{C et=current.div(gamma[0]).scale(-.5/a.area);e[a.a][4]+=et.r;e[a.a][5]+=et.i;}}
      return e;
    }
    double[] metrics(double[] v,int src){
      C sum=new C(0,0);double diss=0,maxJ=0;double[] loss=new double[5];C[] currents={new C(0,0),new C(0,0),new C(0,0),new C(0,0)};
      for(Edge e:edges){C dv=val(v,e.a).sub(val(v,e.b)),out=e.g.mul(dv);diss+=.5*e.g.r*dv.abs2();int ka=m.iz[e.a],la=m.layer[ka];
        double da=e.axis==0||e.axis==1?m.h/2:m.dz[ka]/2;
        loss[la]+=.5*out.abs2()*new C(da/e.area,0).div(gamma[la]).r;
        if(e.axis>=0){int kb=m.iz[e.b],lb=m.layer[kb];double db=e.axis==0||e.axis==1?m.h/2:m.dz[kb]/2;loss[lb]+=.5*out.abs2()*new C(db/e.area,0).div(gamma[lb]).r;}
        else{int el=electrode[e.a];currents[el]=currents[el].sub(out);maxJ=Math.max(maxJ,out.abs()/e.area);loss[4]+=.5*out.abs2()*s.zc(omega).r/e.area;}}
      double sourcePower=0,series=0;for(int j=0;j<2;j++){C u=new C(j==src?.5:0,0),cur=u.sub(val(v,m.n+j)).scale(.02);sourcePower+=.5*u.r*cur.r;series+=.5*50*cur.abs2();}
      for(C c:currents)sum=sum.add(c);
      double powerError=Math.abs(sourcePower-diss-series)/Math.max(sourcePower,1e-30);
      return new double[]{currents[0].abs()/Math.sqrt(2),currents[1].abs()/Math.sqrt(2),currents[2].abs()/Math.sqrt(2),currents[3].abs()/Math.sqrt(2),maxJ/Math.sqrt(2),diss,powerError,sum.abs(),2*val(v,m.n+src).abs(),loss[0],loss[1],loss[2],loss[3],loss[4]};
    }
  }
  static double dot(double[] a,double[] b){double v=0;for(int i=0;i<a.length;i++)v+=a[i]*b[i];return v;}
  static double[][] directions(int count){double[][] d=new double[count+26][3];int at=0;for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++)for(int z=-1;z<=1;z++){double norm=Math.sqrt(x*x+y*y+z*z);if(norm>0)d[at++]=new double[]{x/norm,y/norm,z/norm};}for(int i=0;i<count;i++){double z=1-2*(i+.5)/count,phi=i*Math.PI*(3-Math.sqrt(5));d[i+26]=new double[]{Math.sqrt(1-z*z)*Math.cos(phi),Math.sqrt(1-z*z)*Math.sin(phi),z};}return d;}
  static double ti(double[] a,double[] b,double[][] dirs){double max=0;for(double[] n:dirs){double ar=0,ai=0,br=0,bi=0;for(int k=0;k<3;k++){ar+=n[k]*a[2*k];ai+=n[k]*a[2*k+1];br+=n[k]*b[2*k];bi+=n[k]*b[2*k+1];}max=Math.max(max,2*Math.min(Math.hypot(ar,ai),Math.hypot(br,bi)));}return max;}
  static double[] target(Mesh m,double[][] field,double depth){
    int k=0;while(k<m.nz-2&&m.z[k+1]<depth)k++;double t=(depth-m.z[k])/(m.z[k+1]-m.z[k]);double[] a=new double[6];
    int lo=(m.nx-1)/2,hi=m.nx/2;int count=lo==hi?1:2;
    for(int j=lo;j<=hi;j++)for(int i=lo;i<=hi;i++)for(int c=0;c<6;c++)a[c]+=((1-t)*field[m.at(i,j,k)][c]+t*field[m.at(i,j,k+1)][c])/(count*count);return a;
  }
  static List<Layout> layouts(){List<Layout> all=new ArrayList<Layout>();double[] dist={.0075,.0125,.0175};
    for(double a:dist)for(double b:dist){if(a<b||Math.hypot(a+.005,b+.005)>.025)continue;
      double[][] p={{-a,-b},{a,-b},{a,b},{-a,b}};int[][] patterns={{0,1,2,3},{0,2,1,3},{0,3,1,2}};
      for(int k=0;k<patterns.length;k++){double[][] q=new double[4][];for(int j=0;j<4;j++)q[j]=p[patterns[k][j]];all.add(new Layout(String.format(Locale.US,"a%.1f_b%.1f_p%d",a*1000,b*1000,k),q));}}
    return all;
  }
  static class Result {Layout layout;double target,center,max,maxz,maxx,maxy,res,powerError;double[] m1,m2;double[][] e1,e2;Mesh mesh;}
  static Result run(Mesh m,Scenario s,Layout l,boolean keep){
    Net n1=new Net(m,s,l,2000),n2=new Net(m,s,l,2010);double[] v1=n1.solve(0),v2=n2.solve(1);double[][] e1=n1.field(v1),e2=n2.field(v2);Result r=new Result();r.layout=l;r.mesh=m;
    r.target=ti(target(m,e1,.020),target(m,e2,.020),directions(2048));r.center=ti(target(m,e1,.01255),target(m,e2,.01255),directions(2048));
    double[][] dirs=directions(128);for(int p=0;p<m.n;p++){double t=ti(e1[p],e2[p],dirs);if(t>r.max){r.max=t;r.maxx=m.x[p];r.maxy=m.y[p];r.maxz=m.z[m.iz[p]];}}
    r.m1=n1.metrics(v1,0);r.m2=n2.metrics(v2,1);r.res=Math.max(n1.residual,n2.residual);r.powerError=Math.max(r.m1[6],r.m2[6]);if(keep){r.e1=e1;r.e2=e2;}return r;
  }
  static void export(Result r,String base) throws Exception {
    PrintWriter o=new PrintWriter(base+"-field.csv","UTF-8");o.println("x_mm,y_mm,z_mm,layer,TI_sampled_V_m,E1x_re,E1x_im,E1y_re,E1y_im,E1z_re,E1z_im,E2x_re,E2x_im,E2y_re,E2y_im,E2z_re,E2z_im");double[][] dirs=directions(128);Mesh m=r.mesh;
    for(int p=0;p<m.n;p++){o.printf(Locale.US,"%.6f,%.6f,%.6f,%d,%.9g",m.x[p]*1000,m.y[p]*1000,m.z[m.iz[p]]*1000,m.layer[m.iz[p]],ti(r.e1[p],r.e2[p],dirs));for(double v:r.e1[p])o.printf(Locale.US,",%.9g",v);for(double v:r.e2[p])o.printf(Locale.US,",%.9g",v);o.println();}o.close();
  }
  static void selftest(){
    C a=new C(2,3),b=new C(4,-1);if(a.mul(b).div(b).sub(a).abs()>1e-12)throw new RuntimeException("Complex arithmetic");
    double[][] dirs=directions(1024);if(Math.abs(ti(new double[]{2,0,0,0,0,0},new double[]{1,0,0,0,0,0},dirs)-2)>1e-12)throw new RuntimeException("TI parallel");
    if(Math.abs(ti(new double[]{1,0,0,0,0,0},new double[]{0,0,1,0,0,0},dirs)-Math.sqrt(2))>.02)throw new RuntimeException("TI orthogonal");
    if(ti(new double[6],new double[]{1,0,0,0,0,0},dirs)!=0)throw new RuntimeException("TI zero");
    Mesh mesh=new Mesh(2.5);Net net=new Net(mesh,new Scenario("test",.01,.001,1),layouts().get(0),2000);
    net.edges.clear();net.N=3;net.m.n=1;net.dr=new double[3];net.di=new double[3];
    C upper=new C(120,-30),lower=new C(230,-70);net.add(1,0,new C(1,0).div(upper),0,1);net.add(0,-1,new C(1,0).div(lower),0,1);net.dr[1]+=.02;net.dr[2]+=.02;
    double[] v=net.solve(0);C analytic=lower.scale(.5).div(upper.add(lower).add(new C(50,0)));
    if(net.val(v,0).sub(analytic).abs()>1e-8)throw new RuntimeException("Complex resistor network benchmark");
    System.out.println("Analytic complex-network and envelope tests passed");
  }
  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);selftest();if(args.length>0&&args[0].equals("--selftest"))return;
    Properties cfg=new Properties();File config=new File("simulation.properties");if(config.exists()){InputStream in=new FileInputStream(config);cfg.load(in);in.close();}
    String[] names={"sc","dermis","fat","muscle"};for(int k=0;k<4;k++){SIG[k]=Double.parseDouble(cfg.getProperty(names[k]+".sigma",Double.toString(SIG[k])));ER[k]=Double.parseDouble(cfg.getProperty(names[k]+".epsilon_r",Double.toString(ER[k])));if(!(SIG[k]>0)||!(ER[k]>=0))throw new IllegalArgumentException("Invalid material");}
    if(args.length>0&&args[0].equals("--verify")){
      String bestTarget="",bestCenter="";double maxTarget=-1,maxCenter=-1;
      BufferedReader ranking=new BufferedReader(new FileReader("results/sweep.csv"));String line;ranking.readLine();while((line=ranking.readLine())!=null){String[] c=line.split(",");if(!c[0].equals("baseline"))continue;double t=Double.parseDouble(c[2]),ce=Double.parseDouble(c[3]);if(t>maxTarget){maxTarget=t;bestTarget=c[1];}if(ce>maxCenter){maxCenter=ce;bestCenter=c[1];}}ranking.close();
      PrintWriter vout=new PrintWriter("results/refined-summary.csv","UTF-8");vout.println("layout,target20_V_m,center12_55_V_m,global_sampled_V_m,global_z_mm,current_CH1_RMS_A,current_CH2_RMS_A,surface_J_RMS_upper_A_m2,tissue_contact_power_W,residual,power_error,SC_power_W,dermis_power_W,fat_power_W,muscle_power_W,contact_power_W");
      for(Layout l:layouts())if(l.name.equals(bestTarget)||l.name.equals(bestCenter)){
        Result rr=run(new Mesh(1.25),new Scenario("baseline",.01,.001,1),l,true);
        if(l.name.equals(bestTarget))export(rr,"results/baseline-refined");if(l.name.equals(bestCenter))export(rr,"results/center-refined");
        vout.printf("%s,%.9g,%.9g,%.9g,%.6f,%.9g,%.9g,%.9g,%.9g,%.3g,%.3g",l.name,rr.target,rr.center,rr.max,rr.maxz*1000,Math.hypot(rr.m1[0],rr.m2[0]),Math.hypot(rr.m1[1],rr.m2[1]),Math.hypot(rr.m1[4],rr.m2[4]),rr.m1[5]+rr.m2[5],rr.res,rr.powerError);for(int jj=9;jj<14;jj++)vout.printf(",%.9g",rr.m1[jj]+rr.m2[jj]);vout.println();vout.flush();System.out.printf("Refined %s target=%.9g center=%.9g%n",l.name,rr.target,rr.center);
      }vout.close();return;
    }
    new File("results").mkdirs();PrintWriter effective=new PrintWriter("results/effective-materials.csv","UTF-8");effective.println("layer,sigma_S_m,epsilon_r,status");for(int k=0;k<4;k++)effective.printf("%s,%.9g,%.9g,uncalibrated_hypothesis%n",names[k],SIG[k],ER[k]);effective.close();Mesh mesh=new Mesh(2.5);List<Layout> ls=layouts();
    Scenario[] ss={new Scenario("baseline",.01,.001,1),new Scenario("contact_low",.001,.001,1),new Scenario("contact_high",.1,.001,1),new Scenario("SC_low",.01,.001,.1),new Scenario("SC_high",.01,.001,10)};
    PrintWriter out=new PrintWriter("results/sweep.csv","UTF-8");out.println("scenario,layout,target20_V_m,center12_55_V_m,global_sampled_V_m,max_x_mm,max_y_mm,max_z_mm,target_global_ratio,I_CH1_source_RMS_A,I_CH2_source_RMS_A,max_surface_J_RMS_upper_A_m2,tissue_contact_power_W,residual,power_balance_error,CH1_own_frequency_Vpp,CH2_own_frequency_Vpp");
    PrintWriter pos=new PrintWriter("results/layouts.csv","UTF-8");pos.println("layout,electrode,x_mm,y_mm");for(Layout l:ls)for(int e=0;e<4;e++)pos.printf("%s,%s,%.3f,%.3f%n",l.name,new String[]{"CH1_plus","CH2_plus","GND_A","GND_B"}[e],l.xy[e][0]*1000,l.xy[e][1]*1000);pos.close();
    Result bestBase=null;for(Scenario s:ss){Result best=null;for(Layout l:ls){Result r=run(mesh,s,l,false);out.printf("%s,%s,%.9g,%.9g,%.9g,%.6f,%.6f,%.6f,%.9g,%.9g,%.9g,%.9g,%.9g,%.3g,%.3g,%.9g,%.9g%n",s.name,l.name,r.target,r.center,r.max,r.maxx*1000,r.maxy*1000,r.maxz*1000,r.target/r.max,Math.hypot(r.m1[0],r.m2[0]),Math.hypot(r.m1[1],r.m2[1]),Math.hypot(r.m1[4],r.m2[4]),r.m1[5]+r.m2[5],r.res,r.powerError,r.m1[8],r.m2[8]);out.flush();System.out.printf("%s %s target=%.6g global=%.6g zmax=%.3f mm residual=%.2g%n",s.name,l.name,r.target,r.max,r.maxz*1000,r.res);if(best==null||r.target>best.target)best=r;}
      Result full=run(mesh,s,best.layout,true);export(full,"results/"+s.name+"-best");if(s.name.equals("baseline"))bestBase=full;
    }out.close();
    Result fine=run(new Mesh(1.25),ss[0],bestBase.layout,true);export(fine,"results/baseline-refined");PrintWriter cv=new PrintWriter("results/convergence.txt","UTF-8");cv.printf("Fixed winning layout %s%nCoarse h=2.5mm target %.9g center %.9g%nFine h=1.25mm target %.9g center %.9g%nRelative target change %.6g%nFine residual %.6g%nFine network power balance error %.6g%n",bestBase.layout.name,bestBase.target,bestBase.center,fine.target,fine.center,Math.abs(fine.target-bestBase.target)/fine.target,fine.res,fine.powerError);cv.close();System.out.println("DONE: results/sweep.csv and field exports");
  }
}
