import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

/** Portable one-frequency wrapper. The frozen numerical implementation is inherited. */
public class CenteredPairBasis extends SelectivityShapeBasis {
  static final Path REPO=Paths.get("/workspace/ngg-tis-task1");
  static final Path SOURCE=Paths.get("/dev/shm/task1-centered-c1-y0-20261025-source");
  static final String CASE="centered-square15-C1-y0-xy80-f3000";
  static final String SCHEMA="task1-centered-c1-y0-native-v1";

  static void regular(Path p)throws Exception{
    require(p.isAbsolute()&&p.equals(p.normalize())&&p.equals(p.toRealPath())&&
      Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS),"Canonical regular pinned file required");
  }
  static Map<String,String> json(Path p)throws Exception{
    regular(p);require(Files.size(p)<=4*1024*1024,"Bounded registration/controller metadata required");
    return new ControllerJson(Files.readString(p,StandardCharsets.UTF_8)).fields();
  }
  static int[] commandContract(List<String> argv){
    int script=-1,execute=-1,output=-1;
    for(int i=0;i<argv.size();i++){
      Path name=Paths.get(argv.get(i)).getFileName();
      if(name!=null&&name.toString().equals("centered_run.py")){require(script<0,"Repeated controller");script=i;}
      if(argv.get(i).equals("--execute")){require(execute<0,"Repeated execute");execute=i;}
      if(argv.get(i).equals("--output")){require(output<0,"Repeated output");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),"Exact new centered_run.py --execute --output parent required");
    return new int[]{script,output};
  }
  static Path pathsGuard(Path run,Path config,Path basis)throws Exception{
    require(run.isAbsolute()&&run.equals(run.normalize())&&run.equals(run.toRealPath())&&
      Files.isDirectory(run,LinkOption.NOFOLLOW_LINKS)&&run.getParent().equals(Paths.get("/dev/shm").toRealPath())&&
      run.getFileName().toString().startsWith("task1-centered-c1-y0-20261025-run")&&
      Files.getFileStore(run).type().equals("tmpfs"),"Approved own canonical tmpfs run required");
    require(config.equals(run.resolve("configs/"+CASE+".properties"))&&basis.equals(run.resolve("bases/"+CASE))&&
      !Files.exists(basis,LinkOption.NOFOLLOW_LINKS),"Exact new config and absent case basis required");
    regular(config);
    for(String d:new String[]{"configs","masks","bases","classes"})
      require(Files.isDirectory(run.resolve(d),LinkOption.NOFOLLOW_LINKS)&&run.resolve(d).equals(run.resolve(d).toRealPath()),"Canonical run directories required");
    return run;
  }
  static void verifyPins(Map<String,String> pre,Path run)throws Exception{
    Map<String,String> sources=new ControllerJson(pre.get("source_sha256")).fields();
    Set<String> names=new HashSet<String>();
    for(String key:sources.keySet()){
      Path p=Paths.get(key);regular(p);String expected=controllerString(sources,key);
      require(expected.matches("[0-9a-f]{64}")&&configHash(Files.readAllBytes(p)).equals(expected),"Frozen source SHA changed");
      names.add(p.getFileName().toString());
    }
    for(String name:new String[]{"TisSweep.java","ExploreBasis.java","SelectivityShapeBasis.java","CenteredPairBasis.java","centered_run.py","centered_inputs.py"})
      require(names.contains(name),"Missing frozen numerical/controller source pin: "+name);
    for(String name:new String[]{"TisSweep.java","ExploreBasis.java","SelectivityShapeBasis.java"}){
      Path original=REPO.resolve("tis-java/"+name);regular(original);
      require(sources.containsKey(original.toString())&&controllerString(sources,original.toString()).equals(configHash(Files.readAllBytes(original))),
        "Numerical source must be the exact SHA-frozen original: "+name);
    }
    Map<String,String> classes=new ControllerJson(pre.get("class_sha256")).fields();
    Set<Path> expected=new HashSet<Path>();
    for(String key:classes.keySet()){
      Path p=Paths.get(key);regular(p);require(p.getParent().equals(run.resolve("classes"))&&p.getFileName().toString().endsWith(".class"),"Only registered compiled classes allowed");
      require(configHash(Files.readAllBytes(p)).equals(controllerString(classes,key)),"Compiled class SHA changed");expected.add(p);
    }
    Set<Path> actual=new HashSet<Path>();
    try(DirectoryStream<Path> files=Files.newDirectoryStream(run.resolve("classes"),"*.class")){for(Path p:files)actual.add(p);}
    require(actual.equals(expected),"All and only actual classes must be pinned");
    for(String name:new String[]{"TisSweep.class","ExploreBasis.class","SelectivityShapeBasis.class","CenteredPairBasis.class"})
      require(expected.contains(run.resolve("classes/"+name)),"Missing numerical class pin");
    for(Class<?> cls:new Class<?>[]{TisSweep.class,ExploreBasis.class,SelectivityShapeBasis.class,CenteredPairBasis.class})
      require(Paths.get(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).toRealPath().equals(run.resolve("classes")),"Loaded numerical classes must be the frozen run classes");
  }
  static Path parentGuard(String[] args,byte[] configBytes,boolean absent)throws Exception{
    require(args.length==5&&args[0].equals("--execute-parent")&&args[1].matches("[1-9][0-9]*")&&args[2].matches("[1-9][0-9]*"),"Exact parent arguments required");
    long pid=Long.parseLong(args[1]),ticks=Long.parseLong(args[2]);parentIdentity(pid,ticks);
    List<String> argv=processArguments(pid);int[] positions=commandContract(argv);
    Path cwd=Paths.get("/proc",args[1],"cwd").toRealPath();
    Path script=cwd.resolve(argv.get(positions[0])).toAbsolutePath().normalize();regular(script);
    require(script.equals(SOURCE.resolve("centered_run.py")),"Exact frozen new controller path required");
    Path run=cwd.resolve(argv.get(positions[1]+1)).toAbsolutePath().normalize();
    Path config=Paths.get(args[3]),basis=Paths.get(args[4]);
    if(absent)pathsGuard(run,config,basis);
    else require(config.equals(run.resolve("configs/"+CASE+".properties"))&&basis.equals(run.resolve("bases/"+CASE))&&
      Files.isDirectory(basis,LinkOption.NOFOLLOW_LINKS),"Exact own created basis required");
    runMarkers(run);Map<String,String> pre=json(run.resolve("preregistration.json")),control=json(run.resolve("controller.json"));
    require(controllerString(pre,"schema").equals(SCHEMA)&&controllerString(pre,"status").equals("prepared")&&
      controllerString(pre,"repository_root").equals(REPO.toString())&&controllerString(pre,"run_directory").equals(run.toString())&&
      controllerString(pre,"case_id").equals(CASE),"Exact frozen preregistration identity required");
    require(controllerString(pre,"controller_path").equals(script.toString())&&
      controllerString(pre,"controller_sha256").equals(configHash(Files.readAllBytes(script))),"Controller source hash changed");
    require(controllerString(control,"status").equals("running")&&controllerString(control,"current_case").equals(CASE)&&
      controllerLong(control,"pid")==pid&&controllerLong(control,"proc_start_ticks")==ticks&&
      controllerString(control,"preregistration_sha256").equals(configHash(Files.readAllBytes(run.resolve("preregistration.json")))),"Live controller/preregistration/PID mismatch");
    String hash=configHash(configBytes);
    require(controllerString(pre,"config_sha256").equals(hash)&&controllerString(control,"current_config_sha256").equals(hash)&&
      Arrays.equals(configBytes,Files.readAllBytes(config)),"Exact unchanged configuration required");
    Properties p=new Properties();p.load(new ByteArrayInputStream(configBytes));
    Path mask=Paths.get(p.getProperty("mask.path"));regular(mask);
    require(mask.equals(run.resolve("masks/"+CASE+".csv"))&&controllerString(pre,"mask_sha256").equals(configHash(Files.readAllBytes(mask)))&&
      p.getProperty("mask.sha256").equals(controllerString(pre,"mask_sha256")),"Exact centered mask pin required");
    verifyPins(pre,run);parentOwnsLock(pid,REPO.resolve(".task1-execution.lock"));runMarkers(run);parentIdentity(pid,ticks);
    return run;
  }
  static void configuration(Properties p){
    require(p.getProperty("frequencies").equals("3000")&&p.getProperty("channels").equals("1")&&
      number(p,"h_mm")==.625&&p.getProperty("validation.sc_cells").equals("2")&&p.getProperty("bulk.counts").equals("14,14,40"),"Only one-output3000Hz fixed fine grid allowed");
    String[] names={"sc","dermis","fat","muscle"};double[] sig={.0002,.2,.04,.3},er={110000,10000,1000,100000};
    for(int k=0;k<4;k++)require(number(p,names[k]+".sigma")==sig[k]&&number(p,names[k]+".epsilon_r")==er[k],"Frozen tissue properties required");
    require(number(p,"z.3000.re")==4.4523250115054224e-05&&number(p,"z.3000.im")==-9.587510512701813e-05,"Nominal PBS10nm/Rs500 specific impedance required");
    for(int e=0;e<2;e++)require(number(p,"pad."+e+".x_mm")==((e==0)?-10:10)&&number(p,"pad."+e+".y_mm")==0&&
      p.getProperty("pad."+e+".shape").equals("rectangle")&&number(p,"pad."+e+".width_mm")==15&&number(p,"pad."+e+".height_mm")==15&&
      number(p,"pad."+e+".rotation_deg")==0&&number(p,"pad."+e+".analytic_area_mm2")==225&&
      Math.abs(number(p,"pad."+e+".represented_area_m2")/.000225-1)<1e-12,"Two centered original square225mm2 pads required");
  }
  static void centeredMask(List<double[]> patches){
    require(patches.size()==1152,"Exactly1152 full-face patches required");Set<String> seen=new HashSet<String>();
    for(double[] a:patches){int p=(int)a[0],i=(int)a[1],j=(int)a[2];
      require(a[0]==p&&a[1]==i&&a[2]==j&&(p==0||p==1)&&i>=((p==0)?12:44)&&i<((p==0)?36:68)&&j>=28&&j<52&&
        Math.abs(a[3]/(.000625*.000625)-1)<1e-12&&seen.add(p+":"+i+":"+j),"Exact translated physical mask required");}
  }
  static void centeredMetadata(File dir,ValidationMesh m,Properties p,String hash)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"centered_pair_native\",\"exporter_class\":\"CenteredPairBasis\",\"numerical_base_class\":\"SelectivityShapeBasis\",\"config_sha256\":\"%s\",\"h_xy_mm\":0.625,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":1,",hash,m.nx,m.nz,m.n);
      out.print("\"sc_cells\":2,\"bulk_layer_counts\":[14,14,40],\"frequencies_Hz\":[3000],\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"unit_source_peak_phasor_V\":{\"real\":0.5,\"imaginary\":0.0},\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"storage\":\"lossless gzip of original little-endian Float64/complex128\",\"side_bottom_boundary\":\"insulating no outside faces; fixed 50mm cylinder staircase mask\",\"z_faces_mm\":[");
      for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}
      out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"new_potential_solves\":1,\"new_native_RHS\":1,\"extra_potential_solves\":0,\"native_field_translation_used\":false}\n");
    }
  }
  static void selftestCentered()throws Exception{
    selftestSelectivity();
    List<String> good=Arrays.asList("python",SOURCE.resolve("centered_run.py").toString(),"--execute","--output","/dev/shm/task1-centered-c1-y0-20261025-run-fixture");
    require(commandContract(good)[0]==1,"New parent fixture");
    boolean rejected=false;try{commandContract(Arrays.asList("python","task1_cloud_batch.py","--execute","--output","x"));}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Old parent must be rejected");
    List<double[]> patches=new ArrayList<double[]>();for(int e=0;e<2;e++)for(int j=28;j<52;j++)for(int i=(e==0?12:44);i<(e==0?36:68);i++)patches.add(new double[]{e,i,j,.000625*.000625});
    centeredMask(patches);patches.get(0)[2]-=16;rejected=false;try{centeredMask(patches);}catch(IllegalStateException e){rejected=true;}
    require(rejected,"Off-centre mask must be rejected");
    Properties p=new Properties();p.setProperty("frequencies","3000");p.setProperty("channels","1");p.setProperty("h_mm",".625");
    p.setProperty("validation.sc_cells","2");p.setProperty("bulk.counts","14,14,40");
    String[] names={"sc","dermis","fat","muscle"},sig={".0002",".2",".04",".3"},er={"110000","10000","1000","100000"};
    for(int k=0;k<4;k++){p.setProperty(names[k]+".sigma",sig[k]);p.setProperty(names[k]+".epsilon_r",er[k]);}
    p.setProperty("z.3000.re","4.4523250115054224e-05");p.setProperty("z.3000.im","-9.587510512701813e-05");
    for(int e=0;e<2;e++){
      String key="pad."+e+".";p.setProperty(key+"x_mm",e==0?"-10":"10");p.setProperty(key+"y_mm","0");p.setProperty(key+"shape","rectangle");
      p.setProperty(key+"width_mm","15");p.setProperty(key+"height_mm","15");p.setProperty(key+"rotation_deg","0");
      p.setProperty(key+"analytic_area_mm2","225");p.setProperty(key+"represented_area_m2",".000225");
    }
    configuration(p);p.setProperty("frequencies","3000,3030,9000,9090");rejected=false;
    try{configuration(p);}catch(IllegalStateException e){rejected=true;}require(rejected,"Four-tone configuration must be rejected");
    p.setProperty("frequencies","3000");p.setProperty("pad.0.y_mm","-10");rejected=false;
    try{configuration(p);}catch(IllegalStateException e){rejected=true;}require(rejected,"Old Y configuration must be rejected");
    System.out.println("CENTERED_SELFTEST newparent/exactmask/onefrequency/centredconfiguration guards passed; inherited numerical selftest; phantomPDE0");
  }
  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestCentered();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only registered new parent or --selftest");
    byte[] configBytes=registeredConfig(args[3]);parentGuard(args,configBytes,true);
    Properties p=new Properties();p.load(new ByteArrayInputStream(configBytes));configuration(p);
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    List<double[]> patches=mask(p);centeredMask(patches);
    ValidationMesh m=new ValidationMesh(.625,2,new int[]{14,14,40});require(m.n==351680,"Exact native cell count required");
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    try(PrintWriter grid=textZipped(dir,"grid.csv")){grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int k=0;k<m.n;k++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[k]*1000,m.y[k]*1000,m.z[m.iz[k]]*1000,m.layer[m.iz[k]],m.h*m.h*m.dz[m.iz[k]]);}
    ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z.3000.re"),number(p,"z.3000.im")),1,3000,patches);
    double[] areas=new double[2];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
    double worstArea=0;for(int e=0;e<2;e++)worstArea=Math.max(worstArea,Math.abs(areas[e]/number(p,"pad."+e+".represented_area_m2")-1));
    require(Double.isFinite(worstArea)&&worstArea<=1e-10,"Physical pad area gate before solve");
    double[][] volts=new double[1][];
    try(DataOutputStream fields=zipped(dir,"field-3000.bin")){volts[0]=net.solve(0);for(double[] row:net.field(volts[0]))for(double value:row)put(fields,value);}
    try(DataOutputStream phi=zipped(dir,"potential-3000.bin")){for(int cell=0;cell<m.n;cell++)put(phi,net.val(volts[0],cell));}
    try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-3000.csv"),"UTF-8")){contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.17g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);}
    try(DataOutputStream density=binary(dir,"density-3000.bin")){for(Contact c:net.contacts)put(density,net.edgeCurrent(c.edge,volts[0]).scale(-1/c.edge.area));}
    C[][][] loss=net.lossMatrices(volts);
    try(DataOutputStream file=binary(dir,"loss-3000.bin")){for(C[][] matrix:loss)for(C[] row:matrix)for(C value:row)put(file,value);}
    C current=new C(.5,0).sub(net.val(volts[0],m.n)).scale(.02);
    try(DataOutputStream file=binary(dir,"source-3000.bin")){put(file,current);}
    double power=.25*current.r,sum=0;for(int k=0;k<6;k++)sum+=loss[k][0][0].r;
    double worstPower=Math.abs(sum-power)/Math.max(Math.abs(power),1e-30);
    C balance=new C(0,0);double magnitude=0;for(Contact c:net.contacts){C value=net.edgeCurrent(c.edge,volts[0]);balance=balance.add(value);magnitude+=value.abs();}
    double worstCurrent=balance.abs()/Math.max(magnitude,1e-30),worstInterface=net.interfaceContinuity(volts[0]),worstResidual=net.residual;
    require(Double.isFinite(worstResidual)&&Double.isFinite(worstPower)&&Double.isFinite(worstCurrent)&&Double.isFinite(worstArea)&&Double.isFinite(worstInterface),"Finite five native gates required");
    require(worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7,"Unchanged native conservation gates failed");
    parentGuard(args,configBytes,false);
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":1,\"cells\":%d,\"h_xy_mm\":0.625,\"sc_cells\":2,\"new_native_RHS\":1}%n",worstResidual,worstPower,worstCurrent,worstArea,worstInterface,m.n);
    }
    centeredMetadata(dir,m,p,configHash(configBytes));new File(dir,"BASIS_COMPLETE").createNewFile();
    System.out.printf("CENTERED f=3000 channels=1 pads=2 cells=%d residual=%.3g power=%.3g current=%.3g interface=%.3g RHS=1%n",m.n,worstResidual,worstPower,worstCurrent,worstInterface);
  }
}
