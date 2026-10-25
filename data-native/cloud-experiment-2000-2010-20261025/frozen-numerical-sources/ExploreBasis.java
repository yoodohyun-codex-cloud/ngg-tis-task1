import java.io.*;
import java.util.*;

/** Linear transfer bases for a common-ground phantom with at most eight pads.
 * Uses the unchanged TisSweep mesh, material law and COCG implementation.
 * Each basis is 0.5 V peak through 50 ohm; all other outputs stay terminated.
 */
public class ExploreBasis extends TisSweep {
  static class Boundary extends Scenario {
    C z;
    Boundary(double re,double im){super("measured",1,0,1);z=new C(re,im);if(re<0)throw new IllegalArgumentException("Nonpassive contact");}
    C zc(double w){return z;}
  }
  static class Contact {Edge edge;int pad;Contact(Edge e,int p){edge=e;pad=p;}}
  static class GNet extends Net {
    int channels;double size;List<Contact> contacts=new ArrayList<Contact>();
    GNet(Mesh m,Scenario s,double[][] xy,double size,int channels,double f){
      super(m,s,TisSweep.layouts().get(0),f);
      this.channels=channels;this.size=size;N=m.n+channels;
      edges.clear();dr=new double[N];di=new double[N];
      if(channels<1||channels>4||xy.length!=2*channels)throw new IllegalArgumentException("At most eight pads");
      for(int e=0;e<xy.length;e++){
        for(int a:new int[]{-1,1})for(int b:new int[]{-1,1})if(Math.hypot(xy[e][0]+a*size/2,xy[e][1]+b*size/2)>.025+1e-12)throw new IllegalArgumentException("Pad outside phantom");
        for(int q=0;q<e;q++)if(Math.abs(xy[e][0]-xy[q][0])<size-1e-12&&Math.abs(xy[e][1]-xy[q][1])<size-1e-12)throw new IllegalArgumentException("Overlapping pads");
      }
      double[] areas=new double[xy.length];
      for(int p=0;p<m.n;p++){
        int i=m.ix[p],j=m.iy[p],k=m.iz[p];C ga=gamma[m.layer[k]];
        int q=m.at(i+1,j,k);if(q>=0)add(p,q,ga.scale(m.dz[k]),0,m.h*m.dz[k]);
        q=m.at(i,j+1,k);if(q>=0)add(p,q,ga.scale(m.dz[k]),1,m.h*m.dz[k]);
        q=m.at(i,j,k+1);if(q>=0){C zz=new C(m.dz[k]/2,0).div(ga).add(new C(m.dz[k+1]/2,0).div(gamma[m.layer[k+1]]));add(p,q,new C(m.h*m.h,0).div(zz),2,m.h*m.h);}
        if(k==0)for(int e=0;e<xy.length;e++){
          double ax=Math.max(0,Math.min(m.x[p]+m.h/2,xy[e][0]+size/2)-Math.max(m.x[p]-m.h/2,xy[e][0]-size/2));
          double ay=Math.max(0,Math.min(m.y[p]+m.h/2,xy[e][1]+size/2)-Math.max(m.y[p]-m.h/2,xy[e][1]-size/2));
          double area=ax*ay;if(area<1e-15)continue;
          C zz=s.zc(omega).add(new C(m.dz[0]/2,0).div(ga));
          add(p,e<channels?m.n+e:-1,new C(area,0).div(zz),-1,area);
          contacts.add(new Contact(edges.get(edges.size()-1),e));areas[e]+=area;
        }
      }
      for(double area:areas)if(Math.abs(area-size*size)>1e-11)throw new IllegalArgumentException("Pad area clipped by mesh");
      for(int c=0;c<channels;c++)dr[m.n+c]+=.02;
    }
    C edgeCurrent(Edge e,double[] v){return e.g.mul(val(v,e.a).sub(val(v,e.b)));}
    double resistance(Edge e,int side){
      int p=side==0?e.a:e.b,k=m.iz[p],l=m.layer[k];
      double d=e.axis==0||e.axis==1?m.h/2:m.dz[k]/2;
      return new C(d/e.area,0).div(gamma[l]).r;
    }
    C[][][] lossMatrices(double[][] v){
      C[][][] q=new C[6][channels][channels];
      for(int k=0;k<6;k++)for(int a=0;a<channels;a++)for(int b=0;b<channels;b++)q[k][a][b]=new C(0,0);
      for(Edge e:edges){
        double[] r=new double[6];r[m.layer[m.iz[e.a]]]+=resistance(e,0);
        if(e.axis>=0)r[m.layer[m.iz[e.b]]]+=resistance(e,1);else r[4]+=s.zc(omega).r/e.area;
        C[] current=new C[channels];for(int a=0;a<channels;a++)current[a]=edgeCurrent(e,v[a]);
        for(int a=0;a<channels;a++)for(int b=0;b<channels;b++){
          C prod=new C(current[a].r,-current[a].i).mul(current[b]).scale(.5);
          for(int k=0;k<5;k++)if(r[k]!=0)q[k][a][b]=q[k][a][b].add(prod.scale(r[k]));
        }
      }
      for(int c=0;c<channels;c++)for(int a=0;a<channels;a++)for(int b=0;b<channels;b++){
        C ia=new C(a==c?.5:0,0).sub(val(v[a],m.n+c)).scale(.02);
        C ib=new C(b==c?.5:0,0).sub(val(v[b],m.n+c)).scale(.02);
        q[5][a][b]=q[5][a][b].add(new C(ia.r,-ia.i).mul(ib).scale(25));
      }
      return q;
    }
  }
  static double number(Properties p,String key){return Double.parseDouble(p.getProperty(key));}
  static void put(DataOutputStream out,double v)throws IOException{out.writeLong(Long.reverseBytes(Double.doubleToLongBits(v)));}
  static void put(DataOutputStream out,C v)throws IOException{put(out,v.r);put(out,v.i);}
  static DataOutputStream binary(File dir,String name)throws IOException{return new DataOutputStream(new BufferedOutputStream(new FileOutputStream(new File(dir,name))));}
  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length!=2)throw new IllegalArgumentException("ExploreBasis config.properties new-output-folder");
    Properties p=new Properties();try(InputStream in=new FileInputStream(args[0])){p.load(in);}
    File dir=new File(args[1]);if(!dir.mkdirs())throw new IOException("Output must be new");
    double h=number(p,"h_mm"),size=number(p,"size_mm")/1000;int channels=(int)number(p,"channels");
    double[][] xy=new double[channels*2][2];for(int e=0;e<xy.length;e++){xy[e][0]=number(p,"pad."+e+".x_mm")/1000;xy[e][1]=number(p,"pad."+e+".y_mm")/1000;}
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    Mesh m=new Mesh(h);
    try(PrintWriter grid=new PrintWriter(new File(dir,"grid.csv"),"UTF-8")){
      grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int i=0;i<m.n;i++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[i]*1000,m.y[i]*1000,m.z[m.iz[i]]*1000,m.layer[m.iz[i]],m.h*m.h*m.dz[m.iz[i]]);
    }
    double worstResidual=0,worstPower=0,worstCurrent=0;
    for(String fs:p.getProperty("frequencies","2000,2010,6000,6030").split(",")){
      double f=Double.parseDouble(fs);GNet net=new GNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),xy,size,channels,f);
      double[][] volts=new double[channels][];
      try(DataOutputStream fields=binary(dir,"field-"+fs+".bin")){
        for(int a=0;a<channels;a++){
          volts[a]=net.solve(a);worstResidual=Math.max(worstResidual,net.residual);
          for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);
        }
      }
      try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-"+fs+".csv"),"UTF-8")){
        contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.12g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);
      }
      try(DataOutputStream currents=binary(dir,"density-"+fs+".bin")){
        for(int a=0;a<channels;a++)for(Contact contact:net.contacts)put(currents,net.edgeCurrent(contact.edge,volts[a]).scale(-1/contact.edge.area));
      }
      C[][][] q=net.lossMatrices(volts);
      try(DataOutputStream loss=binary(dir,"loss-"+fs+".bin")){for(C[][] matrix:q)for(C[] row:matrix)for(C value:row)put(loss,value);}
      try(DataOutputStream transfer=binary(dir,"source-"+fs+".bin")){
        for(int c=0;c<channels;c++)for(int a=0;a<channels;a++)put(transfer,new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02));
      }
      for(int a=0;a<channels;a++){
        C source=new C(.5,0).sub(net.val(volts[a],m.n+a)).scale(.02);double power=.25*source.r,sum=0;
        for(int k=0;k<6;k++)sum+=q[k][a][a].r;
        double error=Math.abs(sum-power)/Math.max(Math.abs(power),1e-30);worstPower=Math.max(worstPower,error);
        C balance=new C(0,0);double magnitude=0;
        for(Contact contact:net.contacts){C current=net.edgeCurrent(contact.edge,volts[a]);balance=balance.add(current);magnitude+=current.abs();}
        worstCurrent=Math.max(worstCurrent,balance.abs()/Math.max(magnitude,1e-30));
      }
      System.out.printf("BASIS f=%.0f channels=%d cells=%d residual=%.3g power=%.3g%n",f,channels,m.n,worstResidual,worstPower);
    }
    if(worstResidual>2e-7||worstPower>2e-7||worstCurrent>2e-6)throw new RuntimeException("Basis conservation failed");
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.16g,\"max_power_error\":%.16g,\"max_current_error\":%.16g,\"channels\":%d,\"cells\":%d}%n",worstResidual,worstPower,worstCurrent,channels,m.n);
    }
    new File(dir,"BASIS_COMPLETE").createNewFile();
  }
}
