import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

/** Versioned mid/high producer; all prior frequency producers remain immutable.
 * Guarded fixed-beat30 mid/high extension. ShapeNet/COCG/field/loss arithmetic is inherited.
 * Each RHS remains0.5V peak through50ohm, with the other output0V/50ohm.
 * Dynamic exports are native bases, not a TIS waveform or activation result.
 */
public class CloudFrequencyMidHighBasis extends CloudShapeBasis {
  static String[] frequencies(Properties p){
    String value=p.getProperty("frequencies");
    require("5000,5030,9030".equals(value),"Only5000,5030,9030 new native frequencies;9000 must reuse cached basis");
    require("2".equals(p.getProperty("channels")),"Exactly two independent outputs required");
    return value.split(",");
  }

  static void frequencyParentGuard(String[] args,byte[] configBytes)throws Exception{
    require(args.length==5&&args[0].equals("--execute-parent"),"Actual solve requires --execute-parent PID startticks config basis-dir");
    require(args[1].matches("[1-9][0-9]*")&&args[2].matches("[1-9][0-9]*"),"Invalid parent PID/startticks");
    long pid=Long.parseLong(args[1]),ticks=Long.parseLong(args[2]);parentIdentity(pid,ticks);
    List<String> argv=processArguments(pid);int script=-1,execute=-1,output=-1;
    for(int i=0;i<argv.size();i++){
      String arg=argv.get(i);
      if(Paths.get(arg).getFileName()!=null&&Paths.get(arg).getFileName().toString().equals("task1_mid_high_carrier.py")){
        require(script<0,"Repeated parent executor script");script=i;
      }
      if(arg.equals("--execute")){require(execute<0,"Repeated parent execute flag");execute=i;}
      if(arg.equals("--output")){require(output<0,"Repeated parent output flag");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),"Parent must be task1_mid_high_carrier.py --execute --output run");
    Path cwd=Paths.get("/proc",Long.toString(pid),"cwd").toRealPath();
    Path scriptPath=cwd.resolve(argv.get(script)).toRealPath();
    Path tools=scriptPath.getParent(),repo=tools==null?null:tools.getParent();
    require(repo!=null&&tools.getFileName().toString().equals("tools")&&
      scriptPath.equals(repo.resolve("tools/task1_mid_high_carrier.py").toRealPath())&&
      Files.isRegularFile(scriptPath,LinkOption.NOFOLLOW_LINKS),"Exact repository lower-carrier controller required");
    Path run=cwd.resolve(argv.get(output+1)).toAbsolutePath().normalize();
    Path config=Paths.get(args[3]).toAbsolutePath().normalize(),basis=Paths.get(args[4]).toAbsolutePath().normalize();
    String condition=cloudPathsGuard(repo,run,config,basis);runMarkers(run);
    Path controller=run.resolve("controller.json");
    require(Files.isRegularFile(controller,LinkOption.NOFOLLOW_LINKS),"Regular controller.json required");
    Map<String,String> fields=new ControllerJson(Files.readString(controller,StandardCharsets.UTF_8)).fields();
    require(controllerString(fields,"status").equals("running")&&controllerString(fields,"current_case").equals(condition),"Controller status/current_case mismatch");
    require(controllerLong(fields,"pid")==pid&&controllerLong(fields,"proc_start_ticks")==ticks,"Controller parent identity mismatch");
    require(controllerString(fields,"current_config_sha256").equals(configHash(configBytes)),"Controller/config SHA256 mismatch");
    Path lock=repo.resolve(".task1-execution.lock");parentOwnsLock(pid,lock);
    Set<String> owned=new HashSet<String>();
    try(DirectoryStream<Path> fds=Files.newDirectoryStream(Paths.get("/proc",Long.toString(pid),"fd"))){
      for(Path fd:fds)try{
        if(!Files.isSameFile(lock,fd))continue;
        for(String line:Files.readAllLines(Paths.get("/proc",Long.toString(pid),"fdinfo",fd.getFileName().toString()),StandardCharsets.UTF_8)){
          String[] v=line.trim().split("\\s+");
          if(v.length==9&&v[0].equals("lock:")&&v[3].equals("ADVISORY")&&v[4].equals("WRITE")&&
            v[5].equals(Long.toString(pid))&&v[7].equals("0")&&v[8].equals("EOF"))owned.add(v[2]);
        }
      }catch(IOException vanished){/* unrelated descriptor may close */}
    }
    require(owned.contains("FLOCK")&&owned.contains("POSIX"),"Parent must own BOTH global execution locks");
    runMarkers(run);parentIdentity(pid,ticks);
  }

  static String frequencyMetadata(ValidationMesh m,Properties p,String hash)throws Exception{
    String[] fs=frequencies(p);StringWriter buffer=new StringWriter();PrintWriter out=new PrintWriter(buffer);
    out.printf("{\"schema_version\":1,\"exporter_kind\":\"mid_high_frequency_native\",\"exporter_class\":\"CloudFrequencyMidHighBasis\",\"numerical_base_class\":\"SelectivityShapeBasis.ShapeNet\",\"config_sha256\":\"%s\",\"h_xy_mm\":%.17g,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":2,\"n_outputs\":2,\"n_pads\":4,\"pad_node_ids\":[0,1,-1,-1],\"n_return_nodes\":1,\"return_topology\":\"common_GND\",",hash,m.h*1000,m.nx,m.nz,m.n);
    out.printf("\"sc_cells\":%d,\"bulk_layer_counts\":[%s],\"frequencies_Hz\":[%s],\"actual_basis_RHS_solves\":%d,\"potential_export_basis_vectors\":%d,\"extra_potential_export_solves\":0,",m.scCells,p.getProperty("bulk.counts"),p.getProperty("frequencies"),2*fs.length,2*fs.length);
    out.print("\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"inactive_source\":\"0V through 50ohm at every other frequency\",\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"storage\":\"lossless gzip of original little-endian Float64/complex128\",\"side_bottom_boundary\":\"insulating no outside faces; fixed 50mm cylinder staircase mask\",\"z_faces_mm\":[");
    for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}
    out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"full_TIS_waveform_or_activation_claim\":false}\n");out.flush();return buffer.toString();
  }

  static void progress(File dir,String status,int requested,int completed,String frequency,int channel)throws Exception{
    Path partial=dir.toPath().resolve("basis-progress.json.partial");
    String receipt=String.format(Locale.US,"{\"schema\":\"task1-frequency-basis-progress-v1\",\"status\":\"%s\",\"requested_basis_RHS_solves\":%d,\"completed_basis_RHS_solves\":%d,\"last_frequency_Hz\":%s,\"last_basis_channel\":%d,\"extra_potential_export_solves\":0}%n",status,requested,completed,frequency==null?"null":frequency,channel);
    Files.writeString(partial,receipt,StandardCharsets.UTF_8);
    Files.move(partial,dir.toPath().resolve("basis-progress.json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
  }

  static Thread watchdog(long pid,long ticks,Path run){
    final long start=System.nanoTime();Thread thread=new Thread(()->{
      try{while(true){Thread.sleep(250);parentIdentity(pid,ticks);runMarkers(run);
        require((System.nanoTime()-start)/1e9<600.,"Per-condition600s deadline");}}
      catch(InterruptedException done){return;}
      catch(Exception blocked){System.err.println("FREQUENCY_PARENT_OR_DEADLINE_STOP: "+blocked);Runtime.getRuntime().halt(78);}
    },"frequency-parent-watchdog");thread.setDaemon(true);thread.start();return thread;
  }

  static void selftestFrequency()throws Exception{
    Properties p=new Properties();p.setProperty("channels","2");p.setProperty("bulk.counts","14,14,40");
    for(String set:new String[]{"5000,5030,9030"}){p.setProperty("frequencies",set);require(frequencies(p).length==3,"Exact allowed set");}
    for(String bad:new String[]{"9000","5000,5030,9000,9030","1000,1030,2000,2030","3000,3030","1000,1030","2000,2030","3000,3030,9000,9090","1030,1000,2000,2030","5000,5030,9030,3000","5000,5030,9030 ","NaN"}){
      p.setProperty("frequencies",bad);boolean rejected=false;try{frequencies(p);}catch(IllegalStateException expected){rejected=true;}require(rejected,"Reject unregistered frequency set");}
    p.setProperty("frequencies","5000,5030,9030");p.setProperty("channels","4");boolean rejected=false;
    try{frequencies(p);}catch(IllegalStateException expected){rejected=true;}require(rejected,"Reject extra independent outputs");p.setProperty("channels","2");
    for(double f:new double[]{5000,5030,9000,9030}){
      Mesh mesh=new Mesh(2.5);ShapeNet net=new ShapeNet(mesh,new Boundary(.01,-.02),2,f,Collections.<double[]>emptyList());
      for(int l=0;l<4;l++)require(net.gamma[l].r==SIG[l]&&Math.abs(net.gamma[l].i-2*Math.PI*f*EPS0*ER[l])<1e-14,"Actual-frequency material admittance");
      net.edges.clear();mesh.n=3;net.N=5;net.dr=new double[5];net.di=new double[5];
      C z1=new C(.0001/.0001,0).div(net.gamma[0]),z2=new C(.005/.0001,0).div(net.gamma[3]);
      net.add(3,0,new C(1,0).div(z1),0,1);net.add(0,-1,new C(1,0).div(z2),0,1);
      net.add(1,-1,new C(1,0),0,1);net.add(2,-1,new C(1,0),0,1);net.dr[3]+=.02;net.dr[4]+=.02;
      double[] v=net.solve(0);C current=new C(.5,0).sub(net.val(v,3)).scale(.02),exact=new C(.5,0).div(z1.add(z2).add(new C(50,0)));
      require(current.sub(exact).abs()/exact.abs()<2e-7&&net.val(v,4).abs()<1e-14,"Actual-frequency independent analytic layered series and passive50ohm output");
    }
    ValidationMesh m=new ValidationMesh(2.5,2,new int[]{14,14,40});
    for(String set:new String[]{"5000,5030,9030"}){
      p.setProperty("frequencies",set);String text=frequencyMetadata(m,p,"fixture");Map<String,String> fields=new ControllerJson(text).fields();
      require(controllerString(fields,"exporter_kind").equals("mid_high_frequency_native")&&fields.get("frequencies_Hz").equals("["+set+"]"),"Honest dynamic exporter/frequency metadata");
      require(Long.parseLong(fields.get("actual_basis_RHS_solves"))==2*frequencies(p).length&&fields.get("extra_potential_export_solves").equals("0"),"Actual RHS/export counts");
    }
    System.out.println("FREQUENCY_SELFTEST actual5k/5030/9k/9030 material+analytic layered circuit, exactfrequency restrictions, dynamicmetadata counts; phantom PDE0");
  }

  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestFrequency();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only guarded mid/high-carrier execution or --selftest");
    byte[] configBytes=registeredConfig(args[3]);frequencyParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    String[] fsAllowed=frequencies(p);
    require(Runtime.getRuntime().availableProcessors()==1&&Runtime.getRuntime().maxMemory()<=2L*1024*1024*1024,"One CPU and heap<=2GiB required");
    int channels=2,sc=Integer.parseInt(p.getProperty("validation.sc_cells"));
    String[] bc=p.getProperty("bulk.counts").split(",");int[] bulk=new int[3];require(bc.length==3,"Three bulk counts required");for(int k=0;k<3;k++)bulk[k]=Integer.parseInt(bc[k]);
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");require(Double.isFinite(SIG[l])&&SIG[l]>0&&Double.isFinite(ER[l])&&ER[l]>=0,"Finite passive material required");}
    for(String fs:fsAllowed)require(Double.isFinite(number(p,"z."+fs+".re"))&&number(p,"z."+fs+".re")>=0&&Double.isFinite(number(p,"z."+fs+".im")),"Finite passive frequency-specific contact required");
    List<double[]> patches=mask(p);ValidationMesh m=new ValidationMesh(number(p,"h_mm"),sc,bulk);
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    Files.writeString(dir.toPath().resolve("runtime-wrapper.json"),"{\"runtime_wrapper_class\":\"CloudFrequencyMidHighBasis\",\"numerical_base_class\":\"SelectivityShapeBasis.ShapeNet\",\"numerical_operator_modified\":false,\"dynamic_frequency_extension\":true,\"original_sources_modified\":false}\n",StandardCharsets.UTF_8);
    int completed=0;String activeFrequency=null;int activeChannel=-1;
    Thread watch=watchdog(Long.parseLong(args[1]),Long.parseLong(args[2]),dir.toPath().getParent().getParent());
    try{
      progress(dir,"running",2*fsAllowed.length,0,null,-1);
      try(PrintWriter grid=textZipped(dir,"grid.csv")){
        grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int k=0;k<m.n;k++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[k]*1000,m.y[k]*1000,m.z[m.iz[k]]*1000,m.layer[m.iz[k]],m.h*m.h*m.dz[m.iz[k]]);
      }
      double worstResidual=0,worstPower=0,worstCurrent=0,worstArea=0,worstInterface=0;
      for(String fs:fsAllowed){
        activeFrequency=fs;parentIdentity(Long.parseLong(args[1]),Long.parseLong(args[2]));
        ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),channels,Double.parseDouble(fs),patches);
        double[] areas=new double[2*channels];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
        for(int e=0;e<areas.length;e++){double expected=number(p,"pad."+e+".represented_area_m2");require(Double.isFinite(expected)&&expected>0,"Expected area must be positive finite");worstArea=Math.max(worstArea,Math.abs(areas[e]/expected-1));}
        require(Double.isFinite(worstArea)&&worstArea<=1e-10,"Physical pad area mismatch before solve");
        double[][] volts=new double[channels][];
        try(DataOutputStream fields=zipped(dir,"field-"+fs+".bin")){
          for(int a=0;a<channels;a++){activeChannel=a;parentIdentity(Long.parseLong(args[1]),Long.parseLong(args[2]));volts[a]=net.solve(a);completed++;worstResidual=Math.max(worstResidual,net.residual);progress(dir,"running",2*fsAllowed.length,completed,fs,a);for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);}
        }
        try(DataOutputStream potential=zipped(dir,"potential-"+fs+".bin")){for(int a=0;a<channels;a++)for(int cell=0;cell<m.n;cell++)put(potential,net.val(volts[a],cell));}
        try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-"+fs+".csv"),"UTF-8")){contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.17g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);}
        try(DataOutputStream currents=binary(dir,"density-"+fs+".bin")){for(int a=0;a<channels;a++)for(Contact c:net.contacts)put(currents,net.edgeCurrent(c.edge,volts[a]).scale(-1/c.edge.area));}
        C[][][] q=net.lossMatrices(volts);
        try(DataOutputStream loss=binary(dir,"loss-"+fs+".bin")){for(C[][] matrix:q)for(C[] row:matrix)for(C value:row)put(loss,value);}
        try(DataOutputStream transfer=binary(dir,"source-"+fs+".bin")){for(int c=0;c<channels;c++)for(int a=0;a<channels;a++)put(transfer,new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02));}
        for(int a=0;a<channels;a++){
          C source=new C(.5,0).sub(net.val(volts[a],m.n+a)).scale(.02);double power=.25*source.r,sum=0;for(int k=0;k<6;k++)sum+=q[k][a][a].r;
          worstPower=Math.max(worstPower,Math.abs(sum-power)/Math.max(Math.abs(power),1e-30));
          C balance=new C(0,0);double magnitude=0;for(Contact c:net.contacts){C current=net.edgeCurrent(c.edge,volts[a]);balance=balance.add(current);magnitude+=current.abs();}
          worstCurrent=Math.max(worstCurrent,balance.abs()/Math.max(magnitude,1e-30));worstInterface=Math.max(worstInterface,net.interfaceContinuity(volts[a]));
        }
        System.out.printf("FREQUENCY f=%s h=%s cells=%d residual=%.3g power=%.3g current=%.3g interface=%.3g%n",fs,p.getProperty("h_mm"),m.n,worstResidual,worstPower,worstCurrent,worstInterface);
      }
      require(Double.isFinite(worstResidual)&&Double.isFinite(worstPower)&&Double.isFinite(worstCurrent)&&Double.isFinite(worstArea)&&Double.isFinite(worstInterface),"Nonfinite validation");
      require(worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7,"Numerical conservation gate failed");
      try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
        out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":2,\"n_outputs\":2,\"n_pads\":4,\"cells\":%d,\"h_xy_mm\":%.17g,\"sc_cells\":%d}%n",worstResidual,worstPower,worstCurrent,worstArea,worstInterface,m.n,m.h*1000,sc);
      }
      Files.writeString(dir.toPath().resolve("mesh-metadata.json"),frequencyMetadata(m,p,configHash(configBytes)),StandardCharsets.UTF_8);
      parentIdentity(Long.parseLong(args[1]),Long.parseLong(args[2]));progress(dir,"complete",2*fsAllowed.length,completed,activeFrequency,activeChannel);new File(dir,"BASIS_COMPLETE").createNewFile();
    }catch(Exception|Error failure){progress(dir,"failed_preserved",2*fsAllowed.length,completed,activeFrequency,activeChannel);throw failure;}
    finally{watch.interrupt();}
  }
}
