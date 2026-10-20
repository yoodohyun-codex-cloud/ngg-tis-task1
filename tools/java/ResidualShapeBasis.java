import java.io.*;
import java.util.*;

/** Single-frequency numerical residual diagnostic, never a new TIS candidate.
 * Cloud guards, FVM operator, field/contact reconstruction and losses are inherited.
 * Only the literal frozen COCG solve's stopping parameter is configurable here.
 */
public class ResidualShapeBasis extends CloudShapeBasis {
  static final String SOLVER_VERSION="literal-frozen-COCG-rtol-v1";
  static final double NATIVE_RESIDUAL_LIMIT=2e-7;

  static void solverParameters(double tolerance,int maxIterations){
    require(tolerance==1e-9||tolerance==1e-11,"Only default1e-9 or tighter1e-11 registered");
    require(maxIterations==12000,"Frozen12000 iteration cap required");
  }

  static class ResidualNet extends ShapeNet {
    final double requestedTolerance;final int maxIterations;
    double recursiveRelativeResidual=Double.NaN;
    ResidualNet(Mesh m,Scenario s,double f,List<double[]> patches,double tolerance,int maximum){
      super(m,s,2,f,patches);solverParameters(tolerance,maximum);
      requestedTolerance=tolerance;maxIterations=maximum;
    }
    double recomputedDiagnosticLimit(){return requestedTolerance==1e-11?1e-9:NATIVE_RESIDUAL_LIMIT;}
    double[] solve(int source){
      require(source==0||source==1,"Exactly two basis outputs");
      residual=Double.NaN;recursiveRelativeResidual=Double.NaN;iterations=0;
      // Literal TisSweep.Net.solve arithmetic/order. Only stop/cap literals become
      // validated parameters; additional assignments are diagnostic receipts.
      int n=2*N;double[] b=new double[n];b[2*(m.n+source)]=.01;
      double[] x=new double[n],r=b.clone(),z=r.clone();pre(z);double[] p=z.clone();C rho=cdot(r,z);double norm=Math.sqrt(dot(b,b));
      for(int it=0;it<maxIterations;it++){
        double[] ap=raw(p);C alpha=rho.div(cdot(p,ap));caxpy(x,alpha,p);caxpy(r,alpha.scale(-1),ap);
        recursiveRelativeResidual=Math.sqrt(dot(r,r))/norm;iterations=it+1;
        if(recursiveRelativeResidual<requestedTolerance){break;}
        z=r.clone();pre(z);C next=cdot(r,z),beta=next.div(rho);double[] np=z.clone();caxpy(np,beta,p);p=np;rho=next;
        if(!Double.isFinite(rho.r)||it==maxIterations-1)throw new RuntimeException("COCG solver failed");
      }
      double[] ax=raw(x);for(int j=0;j<n;j++)ax[j]-=b[j];residual=Math.sqrt(dot(ax,ax)/dot(b,b));
      if(!Double.isFinite(residual)||residual>NATIVE_RESIDUAL_LIMIT)throw new RuntimeException("Residual "+residual);
      if(residual>recomputedDiagnosticLimit())throw new RuntimeException("Stronger diagnostic recomputed residual gate failed: "+residual+" > "+recomputedDiagnosticLimit());
      return x;
    }
  }

  static String finite(double value){return Double.isFinite(value)?Double.toString(value):"null";}
  static class SolveReceipt {
    int channel,iterations;double recursive,recomputed,tolerance;String status;
    SolveReceipt(int channel,ResidualNet net,String status){this.channel=channel;iterations=net.iterations;
      recursive=net.recursiveRelativeResidual;recomputed=net.residual;tolerance=net.requestedTolerance;this.status=status;}
  }
  static void diagnostics(File dir,double tolerance,int maximum,String status,List<SolveReceipt> receipts)throws Exception{
    File temporary=new File(dir,"solver-diagnostics.json.partial");
    try(PrintWriter out=new PrintWriter(temporary,"UTF-8")){
      out.printf("{\"schema\":\"task1-residual-solver-v1\",\"status\":\"%s\",\"solver_version\":\"%s\",\"relative_tolerance\":%.17g,\"max_iterations\":%d,\"native_residual_limit\":2e-7,\"recomputed_diagnostic_limit\":%.17g,\"solves\":[",status,SOLVER_VERSION,tolerance,maximum,tolerance==1e-11?1e-9:NATIVE_RESIDUAL_LIMIT);
      for(int i=0;i<receipts.size();i++){
        if(i>0)out.print(',');SolveReceipt r=receipts.get(i);
        out.printf("{\"basis_channel\":%d,\"iterations\":%d,\"recursive_relative_residual\":%s,\"recomputed_relative_residual\":%s,\"relative_residual\":%s,\"requested_relative_tolerance\":%.17g,\"status\":\"%s\"}",r.channel,r.iterations,finite(r.recursive),finite(r.recomputed),finite(r.recomputed),r.tolerance,r.status);
      }
      out.print("],\"full_TIS_waveform_or_probe_prediction\":false,\"rigorous_forward_error_bound\":false}\n");
    }
    java.nio.file.Files.move(temporary.toPath(),new File(dir,"solver-diagnostics.json").toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING,java.nio.file.StandardCopyOption.ATOMIC_MOVE);
  }

  static ShapeNet circuit(boolean overridden,double tolerance,boolean ladder){
    Mesh mesh=new Mesh(2.5);
    ShapeNet net=overridden?new ResidualNet(mesh,new Boundary(.01,-.02),3000,Collections.<double[]>emptyList(),tolerance,12000):
      new ShapeNet(mesh,new Boundary(.01,-.02),2,3000,Collections.<double[]>emptyList());
    // Bounded20–32ohm shunts give enough attenuation before the256-node
    // Krylov termination cliff to resolve both stopping parameters.
    net.edges.clear();mesh.n=ladder?256:3;net.N=mesh.n+2;net.dr=new double[net.N];net.di=new double[net.N];
    if(ladder){
      for(int i=0;i<mesh.n;i++){
        net.add(i,-1,new C(1,0).div(new C(20+(i%13),-5)),0,1);
        if(i+1<mesh.n)net.add(i,i+1,new C(1,0).div(new C(1+.03*(i%7),-.05)),0,1);
      }
      net.add(mesh.n,0,new C(1,0).div(new C(13,-5)),0,1);
      net.add(mesh.n+1,mesh.n-1,new C(1,0).div(new C(29,-7)),0,1);
    }else{
      net.add(3,0,new C(1,0).div(new C(25,-13)),0,1);
      net.add(0,-1,new C(1,0).div(new C(71,-24)),0,1);
      net.add(1,-1,new C(1,0),0,1);net.add(2,-1,new C(1,0),0,1);
    }
    net.dr[mesh.n]+=.02;net.dr[mesh.n+1]+=.02;return net;
  }
  static void selftestResidual(){
    ResidualNet series=(ResidualNet)circuit(true,1e-11,false);double[] solved=series.solve(0);
    C actual=new C(.5,0).sub(series.val(solved,3)).scale(.02);
    C exact=new C(.5,0).div(new C(25,-13).add(new C(71,-24)).add(new C(50,0)));
    require(actual.sub(exact).abs()/exact.abs()<1e-10,"Independent analytic complex series circuit");
    ShapeNet original=circuit(false,1e-9,true);
    ResidualNet same=(ResidualNet)circuit(true,1e-9,true),tight=(ResidualNet)circuit(true,1e-11,true);
    double[] a=original.solve(0),b=same.solve(0);double originalResidual=original.residual;
    require(a.length==b.length&&original.iterations==same.iterations,"Default inherited solve shape/iteration identity");
    for(int i=0;i<a.length;i++)require(Double.doubleToLongBits(a[i])==Double.doubleToLongBits(b[i]),"Default inherited solve exact vector identity");
    require(Double.doubleToLongBits(originalResidual)==Double.doubleToLongBits(same.residual),"Default inherited exact residual identity");
    tight.solve(0);
    require(tight.residual<same.residual&&tight.iterations>same.iterations,"Tight tolerance must improve tiny-ladder actual residual");
    require(tight.residual<=1e-9&&tight.recursiveRelativeResidual<1e-11,"Tight actual and recursive residual gates");
    boolean rejected=false;try{solverParameters(1e-7,12000);}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Reject loosened tolerance");
    rejected=false;try{solverParameters(1e-11,24000);}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Reject iteration budget expansion");
    System.out.printf("RESIDUAL_SELFTEST analytic complex series; inherited/default exact bitwise vector+iteration+residual; tiny256node lumped ladder default residual=%.17g iterations=%d tight residual=%.17g iterations=%d; forbidden tolerance/cap rejected; phantom PDE0%n",same.residual,same.iterations,tight.residual,tight.iterations);
  }

  static void metadataResidual(File dir,ValidationMesh m,Properties p,String hash,double tolerance,int maximum)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"residual_diagnostic_native\",\"exporter_class\":\"ResidualShapeBasis\",\"numerical_base_class\":\"SelectivityShapeBasis.ShapeNet\",\"config_sha256\":\"%s\",\"h_xy_mm\":%.17g,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":2,\"n_outputs\":2,\"n_pads\":4,\"n_return_nodes\":1,\"return_topology\":\"common_GND\",\"pad_node_ids\":[0,1,-1,-1],",hash,m.h*1000,m.nx,m.nz,m.n);
      out.printf("\"sc_cells\":%d,\"bulk_layer_counts\":[%s],\"frequencies_Hz\":[3000],\"solver_version\":\"%s\",\"solver_relative_tolerance\":%.17g,\"solver_max_iterations\":%d,\"solver_diagnostics_file\":\"solver-diagnostics.json\",",m.scCells,p.getProperty("bulk.counts"),SOLVER_VERSION,tolerance,maximum);
      out.print("\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"inactive_source\":\"0V through50ohm\",\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"storage\":\"grid/field/potential losslessgzip; density/source/loss raw; little-endian Float64/complex128\",\"side_bottom_boundary\":\"insulating no outside faces; fixed50mm cylinder staircase mask\",\"z_faces_mm\":[");
      for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}
      out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"basis_RHS_solves\":2,\"extra_potential_export_solves\":0,\"single_frequency_diagnostic_only\":true,\"frozen_postprocessor_compatible\":false}\n");
    }
  }

  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestResidual();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only exact registered cloud parent or --selftest");
    byte[] configBytes=registeredConfig(args[3]);cloudParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    require(p.getProperty("frequencies").equals("3000"),"Residual diagnostic is exactly3000Hz, not a fullTIS basis");
    require(p.getProperty("channels").equals("2"),"Exactly two outputs/four pads required");
    double tolerance=number(p,"solver.relative_tolerance");int maximum=Integer.parseInt(p.getProperty("solver.max_iterations"));solverParameters(tolerance,maximum);
    double h=number(p,"h_mm");int sc=Integer.parseInt(p.getProperty("validation.sc_cells"));
    require((h==1.25||Math.abs(h-50.0/120)<1e-14)&&sc==2&&p.getProperty("bulk.counts").equals("14,14,40"),"Only default coarse or exactXY120 SC2/bulk14,14,40 diagnostic grids");
    double[][] xy={{-10,-10},{10,10},{10,-10},{-10,10}};
    for(int pad=0;pad<4;pad++)require(p.getProperty("pad."+pad+".shape").equals("rectangle")&&
      number(p,"pad."+pad+".width_mm")==15&&number(p,"pad."+pad+".height_mm")==15&&number(p,"pad."+pad+".rotation_deg")==0&&
      number(p,"pad."+pad+".x_mm")==xy[pad][0]&&number(p,"pad."+pad+".y_mm")==xy[pad][1],"Unchanged four-square baseline geometry required");
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    List<double[]> patches=mask(p);ValidationMesh m=new ValidationMesh(h,sc,new int[]{14,14,40});
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    List<SolveReceipt> receipts=new ArrayList<SolveReceipt>();diagnostics(dir,tolerance,maximum,"running",receipts);
    try{
      try(PrintWriter grid=textZipped(dir,"grid.csv")){
        grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int k=0;k<m.n;k++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[k]*1000,m.y[k]*1000,m.z[m.iz[k]]*1000,m.layer[m.iz[k]],m.h*m.h*m.dz[m.iz[k]]);}
      ResidualNet net=new ResidualNet(m,new Boundary(number(p,"z.3000.re"),number(p,"z.3000.im")),3000,patches,tolerance,maximum);
      double residual=0,power=0,current=0,areaError=0,interfaceError=0;
      double[] areas=new double[4];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
      for(int pad=0;pad<4;pad++){
        double expected=number(p,"pad."+pad+".represented_area_m2");require(expected>0&&Double.isFinite(expected),"Positive finite expected pad area");areaError=Math.max(areaError,Math.abs(areas[pad]/expected-1));}
      require(areaError<=1e-10,"Physical area mismatch before solve");
      double[][] volts=new double[2][];
      try(DataOutputStream fields=zipped(dir,"field-3000.bin")){
        for(int a=0;a<2;a++){
          try{volts[a]=net.solve(a);}catch(Exception error){receipts.add(new SolveReceipt(a,net,"failed"));diagnostics(dir,tolerance,maximum,"failed",receipts);throw error;}
          receipts.add(new SolveReceipt(a,net,"complete"));diagnostics(dir,tolerance,maximum,"running",receipts);
          residual=Math.max(residual,net.residual);for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);
        }
      }
      try(DataOutputStream potential=zipped(dir,"potential-3000.bin")){for(int a=0;a<2;a++)for(int cell=0;cell<m.n;cell++)put(potential,net.val(volts[a],cell));}
      try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-3000.csv"),"UTF-8")){
        contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.17g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);}
      try(DataOutputStream density=binary(dir,"density-3000.bin")){for(int a=0;a<2;a++)for(Contact c:net.contacts)put(density,net.edgeCurrent(c.edge,volts[a]).scale(-1/c.edge.area));}
      C[][][] q=net.lossMatrices(volts);
      try(DataOutputStream loss=binary(dir,"loss-3000.bin")){for(C[][] matrix:q)for(C[] row:matrix)for(C value:row)put(loss,value);}
      try(DataOutputStream transfer=binary(dir,"source-3000.bin")){for(int c=0;c<2;c++)for(int a=0;a<2;a++)put(transfer,new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02));}
      for(int a=0;a<2;a++){
        C source=new C(.5,0).sub(net.val(volts[a],m.n+a)).scale(.02);double supplied=.25*source.r,sum=0;for(int k=0;k<6;k++)sum+=q[k][a][a].r;
        power=Math.max(power,Math.abs(sum-supplied)/Math.max(Math.abs(supplied),1e-30));
        C balance=new C(0,0);double magnitude=0;for(Contact c:net.contacts){C value=net.edgeCurrent(c.edge,volts[a]);balance=balance.add(value);magnitude+=value.abs();}
        current=Math.max(current,balance.abs()/Math.max(magnitude,1e-30));interfaceError=Math.max(interfaceError,net.interfaceContinuity(volts[a]));
      }
      require(Double.isFinite(residual)&&Double.isFinite(power)&&Double.isFinite(current)&&Double.isFinite(areaError)&&Double.isFinite(interfaceError),"Nonfinite residual diagnostic gate");
      require(residual<=2e-7&&power<=2e-7&&current<=2e-6&&areaError<=1e-10&&interfaceError<=2e-7,"Original native conservation gate failed; no threshold relaxation");
      try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
        out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":2,\"n_outputs\":2,\"n_pads\":4,\"cells\":%d,\"h_xy_mm\":%.17g,\"sc_cells\":2}%n",residual,power,current,areaError,interfaceError,m.n,m.h*1000);}
      metadataResidual(dir,m,p,configHash(configBytes),tolerance,maximum);
      diagnostics(dir,tolerance,maximum,"complete",receipts);new File(dir,"BASIS_COMPLETE").createNewFile();
      System.out.printf("RESIDUAL_DIAGNOSTIC f=3000 outputs=2 pads=4 cells=%d stop=%.3g actual=%.3g power=%.3g current=%.3g interface=%.3g%n",m.n,tolerance,residual,power,current,interfaceError);
    }catch(Exception error){diagnostics(dir,tolerance,maximum,"failed",receipts);throw error;}
  }
}
