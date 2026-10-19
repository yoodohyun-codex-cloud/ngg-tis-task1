import java.io.*;
import java.util.*;
import java.nio.file.*;

/** Explicit physical-pad to electrical-node mapping, with exactly two outputs.
 * The existing bulk operator, solver, partial-face E, interface and loss methods
 * are inherited unchanged. No tissue, source or contact law is reimplemented.
 * This is a distinct exporter; the frozen four-pad postprocessor must reject it.
 */
public class GroupedPadBasis extends CloudShapeBasis {
  static void validateNodes(int[] nodes){
    require(nodes.length==4||nodes.length==8||nodes.length==12||nodes.length==16,
      "Physical pad count must be 4, 8, 12 or 16");
    int[] counts=new int[3];
    for(int node:nodes){require(node>=-1&&node<=1,"Pad node must be -1/GND, 0 or 1");counts[node+1]++;}
    require(counts[0]==nodes.length/2&&counts[1]==nodes.length/4&&counts[2]==nodes.length/4,
      "First grouped-pad family requires equal output groups and half return pads");
  }

  static int[] nodes(Properties p){
    require(p.getProperty("channels").equals("2")&&p.getProperty("n_outputs").equals("2"),
      "Grouped pads retain exactly two outputs; channels denotes outputs only");
    int count=Integer.parseInt(p.getProperty("n_pads"));validateNodeCount(count);
    int[] nodes=new int[count];
    for(int i=0;i<nodes.length;i++)nodes[i]=Integer.parseInt(p.getProperty("pad.node."+i));
    validateNodes(nodes);return nodes;
  }

  static void validateNodeCount(int count){
    require(count==4||count==8||count==12||count==16,"Unregistered physical pad count");
  }

  static class GroupNet extends ShapeNet {
    final int[] padNodes;
    GroupNet(Mesh m,Scenario s,double f,List<double[]> patches,int[] nodes){
      // The empty-mask parent builds the identical bulk and both 50ohm nodes.
      super(m,s,2,f,Collections.<double[]>emptyList());
      validateNodes(nodes);padNodes=nodes.clone();double[] covered=new double[m.n];
      double[] areaByPad=new double[nodes.length];
      for(double[] row:patches){
        require(row.length==4,"Grouped mask row must have four columns");
        for(int k=0;k<4;k++)require(Double.isFinite(row[k]),"Nonfinite grouped contact");
        for(int k=0;k<3;k++)require(row[k]>=0&&row[k]==Math.rint(row[k]),"Integer mask IDs required");
        int pad=(int)row[0],i=(int)row[1],j=(int)row[2],cell=m.at(i,j,0);double area=row[3];
        require(pad>=0&&pad<nodes.length&&cell>=0&&area>0&&area<=m.h*m.h*(1+1e-10),
          "Invalid grouped fractional contact");
        covered[cell]+=area;require(covered[cell]<=m.h*m.h*(1+1e-10),"Overlapping grouped cell faces");
        C zz=s.zc(omega).add(new C(m.dz[0]/2,0).div(gamma[0]));
        int node=nodes[pad]<0?-1:m.n+nodes[pad];
        add(cell,node,new C(area,0).div(zz),-1,area);
        contacts.add(new Contact(edges.get(edges.size()-1),pad));areaByPad[pad]+=area;
      }
      for(double area:areaByPad)require(area>0&&Double.isFinite(area),"Every physical pad must have contact area");
    }
    double[] solve(int source){require(source==0||source==1,"Exactly two basis outputs");return super.solve(source);}
  }

  static double compare(double[] a,double[] b){
    require(a.length==b.length,"Regression array shape");double delta=0,scale=0;
    for(int i=0;i<a.length;i++){delta=Math.max(delta,Math.abs(a[i]-b[i]));scale=Math.max(scale,Math.abs(a[i]));}
    return delta/Math.max(scale,1e-30);
  }
  static void regression(ShapeNet reference,ShapeNet candidate,double[][] vectors){
    for(double[] v:vectors){
      require(compare(reference.raw(v),candidate.raw(v))<2e-12,"Grouped operator regression");
      double[][] a=reference.field(v),b=candidate.field(v);
      double delta=0,scale=0;
      for(int i=0;i<a.length;i++)for(int j=0;j<6;j++){
        delta=Math.max(delta,Math.abs(a[i][j]-b[i][j]));scale=Math.max(scale,Math.abs(a[i][j]));}
      require(delta/Math.max(scale,1e-30)<2e-12,"Grouped field regression");
    }
    C[][][] a=reference.lossMatrices(vectors),b=candidate.lossMatrices(vectors);double delta=0,scale=0;
    for(int k=0;k<6;k++)for(int i=0;i<2;i++)for(int j=0;j<2;j++){
      delta=Math.max(delta,a[k][i][j].sub(b[k][i][j]).abs());scale=Math.max(scale,a[k][i][j].abs());}
    require(delta/Math.max(scale,1e-30)<2e-12,"Grouped loss/source-resistor regression");
  }
  static void selftestGrouped(){
    ValidationMesh m=new ValidationMesh(2.5,2,new int[]{14,14,40});
    List<double[]> mask=new ArrayList<double[]>();double[][] xy={{-.01,-.01},{.01,.01},{.01,-.01},{-.01,.01}};
    for(int cell=0;cell<m.n;cell++)if(m.iz[cell]==0)for(int pad=0;pad<4;pad++)
      if(Math.abs(m.x[cell]-xy[pad][0])<.0075&&Math.abs(m.y[cell]-xy[pad][1])<.0075)
        mask.add(new double[]{pad,m.ix[cell],m.iy[cell],m.h*m.h});
    ShapeNet reference=new ShapeNet(m,new Boundary(.01,-.02),2,3000,mask);
    double[][] vectors=new double[2][2*reference.N];
    for(int i=0;i<vectors[0].length;i++){vectors[0][i]=Math.sin(i*.123)*.3;vectors[1][i]=Math.cos(i*.171)*.2;}
    regression(reference,new GroupNet(m,new Boundary(.01,-.02),3000,mask,new int[]{0,1,-1,-1}),vectors);
    for(int split=2;split<=4;split++){
      int[] nodes=new int[4*split];List<double[]> divided=new ArrayList<double[]>();
      for(int pad=0;pad<4;pad++)for(int j=0;j<split;j++)nodes[pad*split+j]=pad<2?pad:-1;
      for(double[] patch:mask)for(int j=0;j<split;j++)
        divided.add(new double[]{patch[0]*split+j,patch[1],patch[2],patch[3]/split});
      regression(reference,new GroupNet(m,new Boundary(.01,-.02),3000,divided,nodes),vectors);
    }
    boolean rejected=false;try{validateNodes(new int[]{0,1,2,-1});}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Reject extra output node");
    rejected=false;try{validateNodes(new int[]{0,0,-1,-1});}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Reject missing second output");
    System.out.println("GROUPED_SELFTEST 4pad original operator/E/loss identity; 8/12/16 zero-gap contact bookkeeping aggregate identity; invalid extra/missing outputs rejected; phantom PDE0. This does not validate physically separated strip geometry or convergence.");
  }

  static void groupedMetadata(File dir,ValidationMesh m,Properties p,int[] nodes,String hash)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"grouped_native\",\"exporter_class\":\"GroupedPadBasis\",\"numerical_base_class\":\"SelectivityShapeBasis\",\"config_sha256\":\"%s\",\"h_xy_mm\":%.17g,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":2,\"n_outputs\":2,\"n_pads\":%d,\"n_return_nodes\":1,\"return_topology\":\"common_GND\",\"pad_node_ids\":%s,",hash,m.h*1000,m.nx,m.nz,m.n,nodes.length,Arrays.toString(nodes));
      out.printf("\"sc_cells\":%d,\"bulk_layer_counts\":[%s],\"frequencies_Hz\":[%s],",m.scCells,p.getProperty("bulk.counts"),p.getProperty("frequencies"));
      out.print("\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"inactive_source\":\"0V through 50ohm at every other frequency\",\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"storage\":\"lossless gzip little-endian Float64/complex128; basis dimension is two outputs\",\"side_bottom_boundary\":\"insulating no outside faces; fixed 50mm cylinder staircase mask\",\"z_faces_mm\":[");
      for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}
      out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"new_potential_solves\":0,\"frozen_four_pad_postprocessor_compatible\":false}\n");
    }
  }

  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestGrouped();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only guarded registered parent execution or --selftest");
    byte[] configBytes=registeredConfig(args[3]);cloudParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    require(p.getProperty("frequencies").equals("3000,3030,9000,9090"),"Initial grouped exporter uses later carrier/harmonic branch only");
    int[] nodes=nodes(p);int sc=Integer.parseInt(p.getProperty("validation.sc_cells"));
    String[] bc=p.getProperty("bulk.counts").split(",");int[] bulk=new int[3];for(int k=0;k<3;k++)bulk[k]=Integer.parseInt(bc[k]);
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    List<double[]> patches=mask(p);ValidationMesh m=new ValidationMesh(number(p,"h_mm"),sc,bulk);
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    try(PrintWriter grid=textZipped(dir,"grid.csv")){
      grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int k=0;k<m.n;k++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[k]*1000,m.y[k]*1000,m.z[m.iz[k]]*1000,m.layer[m.iz[k]],m.h*m.h*m.dz[m.iz[k]]);
    }
    double residual=0,power=0,current=0,areaError=0,interfaceError=0;
    for(String fs:p.getProperty("frequencies").split(",")){
      GroupNet net=new GroupNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),Double.parseDouble(fs),patches,nodes);
      double[] areas=new double[nodes.length];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
      for(int pad=0;pad<nodes.length;pad++){
        double expected=number(p,"pad."+pad+".represented_area_m2");require(expected>0&&Double.isFinite(expected),"Expected pad area positive finite");areaError=Math.max(areaError,Math.abs(areas[pad]/expected-1));}
      require(areaError<=1e-10,"Physical grouped pad area mismatch before solve");
      double[][] volts=new double[2][];
      try(DataOutputStream fields=zipped(dir,"field-"+fs+".bin")){
        for(int a=0;a<2;a++){volts[a]=net.solve(a);residual=Math.max(residual,net.residual);for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);}
      }
      try(DataOutputStream potential=zipped(dir,"potential-"+fs+".bin")){for(int a=0;a<2;a++)for(int cell=0;cell<m.n;cell++)put(potential,net.val(volts[a],cell));}
      try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-"+fs+".csv"),"UTF-8")){
        contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.17g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);}
      try(DataOutputStream density=binary(dir,"density-"+fs+".bin")){for(int a=0;a<2;a++)for(Contact c:net.contacts)put(density,net.edgeCurrent(c.edge,volts[a]).scale(-1/c.edge.area));}
      C[][][] q=net.lossMatrices(volts);
      try(DataOutputStream loss=binary(dir,"loss-"+fs+".bin")){for(C[][] matrix:q)for(C[] row:matrix)for(C value:row)put(loss,value);}
      try(DataOutputStream transfer=binary(dir,"source-"+fs+".bin")){for(int c=0;c<2;c++)for(int a=0;a<2;a++)put(transfer,new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02));}
      for(int a=0;a<2;a++){
        C source=new C(.5,0).sub(net.val(volts[a],m.n+a)).scale(.02);double supplied=.25*source.r,sum=0;for(int k=0;k<6;k++)sum+=q[k][a][a].r;
        power=Math.max(power,Math.abs(sum-supplied)/Math.max(Math.abs(supplied),1e-30));
        C balance=new C(0,0);double magnitude=0;for(Contact c:net.contacts){C value=net.edgeCurrent(c.edge,volts[a]);balance=balance.add(value);magnitude+=value.abs();}
        current=Math.max(current,balance.abs()/Math.max(magnitude,1e-30));interfaceError=Math.max(interfaceError,net.interfaceContinuity(volts[a]));
      }
      System.out.printf("GROUPED f=%s pads=%d outputs=2 cells=%d residual=%.3g power=%.3g current=%.3g interface=%.3g%n",fs,nodes.length,m.n,residual,power,current,interfaceError);
    }
    require(Double.isFinite(residual)&&Double.isFinite(power)&&Double.isFinite(current)&&Double.isFinite(areaError)&&Double.isFinite(interfaceError),"Nonfinite grouped conservation result");
    require(residual<=2e-7&&power<=2e-7&&current<=2e-6&&areaError<=1e-10&&interfaceError<=2e-7,"Grouped numerical conservation gate failed");
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":2,\"n_outputs\":2,\"n_pads\":%d,\"cells\":%d,\"h_xy_mm\":%.17g,\"sc_cells\":%d}%n",residual,power,current,areaError,interfaceError,nodes.length,m.n,m.h*1000,sc);}
    groupedMetadata(dir,m,p,nodes,configHash(configBytes));new File(dir,"BASIS_COMPLETE").createNewFile();
  }
}
