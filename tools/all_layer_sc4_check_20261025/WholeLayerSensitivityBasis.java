import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

/** Four-frequency/two-output SC4 check. Frozen FVM math is inherited.
 * This is NOT a calibrated material reset or a reproduction of phantom papers.
 * Only SC cell count changes2to4 versus the completed SC2 sensitivity. Material
 * values including SCepsilon1100 are identical uncalibrated assumptions. Derived J arrays
 * are gamma*E and sigma*E of the same stored E, not an independent check.
 */
public class WholeLayerSensitivityBasis extends SelectivityShapeBasis {
  static final Path REPO=Paths.get("/workspace/ngg-tis-task1");
  static final Path SOURCE=Paths.get("/dev/shm/task1-all-layer-sc4-check-20261025/source");
  static final String CASE="baseline-square15-sc-eps1100-sc4-xy80";
  static final String SCHEMA="task1-whole-layer-sc4-check-native-v1";

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
      if(name!=null&&name.toString().equals("all_layer_run.py")){require(script<0,"Repeated controller");script=i;}
      if(argv.get(i).equals("--execute")){require(execute<0,"Repeated execute");execute=i;}
      if(argv.get(i).equals("--output")){require(output<0,"Repeated output");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),"Exact new all_layer_run.py --execute --output parent required");
    return new int[]{script,output};
  }
  static Path pathsGuard(Path run,Path config,Path basis)throws Exception{
    require(run.isAbsolute()&&run.equals(run.normalize())&&run.equals(run.toRealPath())&&
      Files.isDirectory(run,LinkOption.NOFOLLOW_LINKS)&&run.getParent().equals(Paths.get("/dev/shm").toRealPath())&&
      run.getFileName().toString().startsWith("task1-all-layer-sc4-check-20261025-run")&&
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
    for(String name:new String[]{"TisSweep.java","ExploreBasis.java","SelectivityShapeBasis.java","WholeLayerSensitivityBasis.java","all_layer_run.py","all_layer_inputs.py"})
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
    for(String name:new String[]{"TisSweep.class","ExploreBasis.class","SelectivityShapeBasis.class","WholeLayerSensitivityBasis.class"})
      require(expected.contains(run.resolve("classes/"+name)),"Missing numerical class pin");
    for(Class<?> cls:new Class<?>[]{TisSweep.class,ExploreBasis.class,SelectivityShapeBasis.class,WholeLayerSensitivityBasis.class})
      require(Paths.get(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).toRealPath().equals(run.resolve("classes")),"Loaded numerical classes must be the frozen run classes");
  }
  static Path parentGuard(String[] args,byte[] configBytes,boolean absent)throws Exception{
    require(args.length==5&&args[0].equals("--execute-parent")&&args[1].matches("[1-9][0-9]*")&&args[2].matches("[1-9][0-9]*"),"Exact parent arguments required");
    long pid=Long.parseLong(args[1]),ticks=Long.parseLong(args[2]);parentIdentity(pid,ticks);
    List<String> argv=processArguments(pid);int[] positions=commandContract(argv);
    Path cwd=Paths.get("/proc",args[1],"cwd").toRealPath();
    Path script=cwd.resolve(argv.get(positions[0])).toAbsolutePath().normalize();regular(script);
    require(script.equals(SOURCE.resolve("all_layer_run.py")),"Exact frozen new controller path required");
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
      p.getProperty("mask.sha256").equals(controllerString(pre,"mask_sha256")),"Exact all-layer sensitivity mask pin required");
    verifyPins(pre,run);parentOwnsLock(pid,REPO.resolve(".task1-execution.lock"));parentOwnsLock(pid,REPO.resolve(".task1-loop.lock"));runMarkers(run);parentIdentity(pid,ticks);
    return run;
  }
  static final String[] LAYERS={"sc","dermis","fat","muscle"};
  static final String[] FREQUENCIES={"3000","3030","9000","9090"};
  static void configuration(Properties p){
    require(p.getProperty("frequencies").equals("3000,3030,9000,9090")&&p.getProperty("channels").equals("2")&&
      number(p,"h_mm")==.625&&p.getProperty("validation.sc_cells").equals("4")&&p.getProperty("bulk.counts").equals("14,14,40")&&
      number(p,"validation.max_cells")==800000,"Exact canonical four-pad/four-frequency SC4 XY80 grid required");
    double[] sig={.0002,.2,.04,.3},er={1100,10000,1000,100000};
    for(int k=0;k<4;k++)require(number(p,LAYERS[k]+".sigma")==sig[k]&&number(p,LAYERS[k]+".epsilon_r")==er[k],
      "Unchanged completed SC2 sensitivity material hypotheses; no material adjustment");
    double[][] z={{4.4523250115054224e-05,-9.587510512701813e-05},{4.407669448241336e-05,-9.563561408953766e-05},
      {4.4451099045190295e-05,-9.508107221709578e-05},{4.462269396972829e-05,-9.543844896710299e-05}};
    for(int f=0;f<4;f++)require(number(p,"z."+FREQUENCIES[f]+".re")==z[f][0]&&number(p,"z."+FREQUENCIES[f]+".im")==z[f][1],
      "Frozen nominal PBS10nm/Rs500 contact values required; not a validated skin contact");
    double[][] xy={{-10,-10},{10,10},{10,-10},{-10,10}};
    for(int e=0;e<4;e++)require(number(p,"pad."+e+".x_mm")==xy[e][0]&&number(p,"pad."+e+".y_mm")==xy[e][1]&&
      p.getProperty("pad."+e+".shape").equals("rectangle")&&number(p,"pad."+e+".width_mm")==15&&number(p,"pad."+e+".height_mm")==15&&
      number(p,"pad."+e+".rotation_deg")==0&&number(p,"pad."+e+".analytic_area_mm2")==225&&
      Math.abs(number(p,"pad."+e+".represented_area_m2")/.000225-1)<1e-12,"Four canonical square225mm2 pads required");
  }
  static void canonicalMask(List<double[]> patches){
    require(patches.size()==2304,"Exactly2304 full-face square patches required");Set<String> seen=new HashSet<String>();
    int[] i0={12,44,44,12},j0={12,44,12,44};
    for(double[] a:patches){int p=(int)a[0],i=(int)a[1],j=(int)a[2];
      require(a[0]==p&&a[1]==i&&a[2]==j&&p>=0&&p<4&&i>=i0[p]&&i<i0[p]+24&&j>=j0[p]&&j<j0[p]+24&&
        Math.abs(a[3]/(.000625*.000625)-1)<1e-12&&seen.add(p+":"+i+":"+j),"Exact frozen baseline mask required");}
  }
  static void writeMetadata(File dir,ValidationMesh m,Properties p,String hash)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"whole_layer_sc4_adjacency_check_native\",\"exporter_class\":\"WholeLayerSensitivityBasis\",\"numerical_base_class\":\"SelectivityShapeBasis\",\"config_sha256\":\"%s\",\"h_xy_mm\":0.625,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":2,",hash,m.nx,m.nz,m.n);
      out.print("\"sc_cells\":4,\"bulk_layer_counts\":[14,14,40],\"frequencies_Hz\":[3000,3030,9000,9090],\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"unit_source_peak_phasor_V\":{\"real\":0.5,\"imaginary\":0.0},\"inactive_output_at_each_basis_frequency\":\"0V through50ohm\",\"pad_to_node\":{\"0\":\"out0\",\"1\":\"out1\",\"2\":\"GND\",\"3\":\"GND\"},\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"current_density_export\":\"Jtotal=gamma*stored_E and Jconduction=sigma*stored_E; derived, not independent verification\",\"storage\":\"lossless gzip little-endian Float64/complex128\",\"side_bottom_boundary\":\"insulating no outside faces; fixed50mm cylinder staircase mask\",\"z_faces_mm\":[");
      for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}
      out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"new_potential_solves\":8,\"new_native_RHS\":8,\"new_native_conditions\":1,\"extra_potential_solves\":0,\"material_calibrated\":false,\"material_scenario\":\"unchanged SC2 material hypotheses including SCepsilon1100; only SCcells2to4\",\"sigma_epsilon_frequency_dispersion_model\":false}\n");
    }
  }
  static void materialAudit(PrintWriter out,ShapeNet net,String fs,boolean comma){
    if(comma)out.print(',');out.printf("{\"frequency_Hz\":%s,\"layers\":[",fs);
    for(int l=0;l<4;l++){
      if(l>0)out.print(',');C gamma=net.gamma[l];
      out.printf("{\"name\":\"%s\",\"sigma_S_m\":%.17g,\"epsilon_r\":%.17g,\"gamma_real_S_m\":%.17g,\"gamma_imag_S_m\":%.17g,\"imag_to_real_ratio\":%.17g,\"measured\":false}",LAYERS[l],SIG[l],ER[l],gamma.r,gamma.i,gamma.i/gamma.r);
    }
    out.print("]}");
  }
  static void selftestSensitivity()throws Exception{
    selftestSelectivity();
    List<String> good=Arrays.asList("python",SOURCE.resolve("all_layer_run.py").toString(),"--execute","--output","/dev/shm/task1-all-layer-sc4-check-20261025-run-fixture");
    require(commandContract(good)[0]==1,"Exact all-layer parent fixture");
    List<double[]> patches=new ArrayList<double[]>();int[] i0={12,44,44,12},j0={12,44,12,44};
    for(int p=0;p<4;p++)for(int j=j0[p];j<j0[p]+24;j++)for(int i=i0[p];i<i0[p]+24;i++)patches.add(new double[]{p,i,j,.000625*.000625});
    canonicalMask(patches);patches.get(0)[2]+=24;boolean rejected=false;
    try{canonicalMask(patches);}catch(IllegalStateException e){rejected=true;}require(rejected,"Changed baseline mask must fail");
    C gamma=new C(.0002,2*Math.PI*3000*EPS0*1100),E=new C(3,-4),J=gamma.mul(E);
    require(Math.abs(J.r-(gamma.r*3+gamma.i*4))<1e-15&&Math.abs(J.i-(-gamma.r*4+gamma.i*3))<1e-15,"Derived complex J sign fixture");
    System.out.println("WHOLE_LAYER_SC4_CHECK_SELFTEST inherited FVM/analytic circuit, exact mask and derived-J complex signs passed; phantomPDE0");
  }
  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestSensitivity();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only registered new parent or --selftest");
    byte[] configBytes=registeredConfig(args[3]);parentGuard(args,configBytes,true);
    Properties p=new Properties();p.load(new ByteArrayInputStream(configBytes));configuration(p);
    for(int l=0;l<4;l++){SIG[l]=number(p,LAYERS[l]+".sigma");ER[l]=number(p,LAYERS[l]+".epsilon_r");}
    List<double[]> patches=mask(p);canonicalMask(patches);
    ValidationMesh m=new ValidationMesh(.625,4,new int[]{14,14,40});require(m.n==361728,"Exact preregistered SC4 native cell count");
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be absent and new");
    try(PrintWriter grid=textZipped(dir,"grid.csv")){grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int cell=0;cell<m.n;cell++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[cell]*1000,m.y[cell]*1000,m.z[m.iz[cell]]*1000,m.layer[m.iz[cell]],m.h*m.h*m.dz[m.iz[cell]]);}
    double worstResidual=0,worstPower=0,worstCurrent=0,worstArea=0,worstInterface=0;
    int rhsCompleted=0;
    try(PrintWriter audit=new PrintWriter(new File(dir,"effective-materials.json"),"UTF-8")){
      audit.print("{\"schema\":\"task1-effective-materials-v1\",\"sigma_unit\":\"S/m\",\"epsilon_r_unit\":\"dimensionless\",\"gamma_unit\":\"S/m\",\"gamma_formula\":\"sigma+j2pi*f*epsilon0*epsilon_r\",\"epsilon0_F_m\":8.8541878128e-12,\"material_status\":\"explicit uncalibrated sensitivity assumptions, NOT measured phantom data\",\"frequency_dependent_sigma_epsilon\":false,\"rows\":[");
      int fi=0;
      for(String fs:FREQUENCIES){
        parentGuard(args,configBytes,false);
        ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),2,Double.parseDouble(fs),patches);
        materialAudit(audit,net,fs,fi++>0);audit.flush();
        double[] areas=new double[4];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
        for(int e=0;e<4;e++)worstArea=Math.max(worstArea,Math.abs(areas[e]/number(p,"pad."+e+".represented_area_m2")-1));
        require(Double.isFinite(worstArea)&&worstArea<=1e-10,"Physical pad area before actual solve");
        double[][] volts=new double[2][];
        try(DataOutputStream fields=zipped(dir,"field-"+fs+".bin");DataOutputStream total=zipped(dir,"Jtotal-"+fs+".bin");DataOutputStream conduction=zipped(dir,"Jconduction-"+fs+".bin")){
          for(int a=0;a<2;a++){
            volts[a]=net.solve(a);rhsCompleted++;worstResidual=Math.max(worstResidual,net.residual);
            double[][] value=net.field(volts[a]);
            for(int cell=0;cell<m.n;cell++)for(int xyz=0;xyz<3;xyz++){
              C e=new C(value[cell][2*xyz],value[cell][2*xyz+1]);int layer=m.layer[m.iz[cell]];
              put(fields,e);put(total,net.gamma[layer].mul(e));put(conduction,e.scale(SIG[layer]));
            }
          }
        }
        try(DataOutputStream phi=zipped(dir,"potential-"+fs+".bin")){for(int a=0;a<2;a++)for(int cell=0;cell<m.n;cell++)put(phi,net.val(volts[a],cell));}
        try(PrintWriter contacts=new PrintWriter(new File(dir,"contacts-"+fs+".csv"),"UTF-8")){contacts.println("pad,x_mm,y_mm,area_m2");for(Contact c:net.contacts)contacts.printf("%d,%.12g,%.12g,%.17g%n",c.pad,m.x[c.edge.a]*1000,m.y[c.edge.a]*1000,c.edge.area);}
        try(DataOutputStream density=binary(dir,"density-"+fs+".bin")){for(int a=0;a<2;a++)for(Contact c:net.contacts)put(density,net.edgeCurrent(c.edge,volts[a]).scale(-1/c.edge.area));}
        C[][][] loss=net.lossMatrices(volts);
        try(DataOutputStream file=binary(dir,"loss-"+fs+".bin")){for(C[][] matrix:loss)for(C[] row:matrix)for(C value:row)put(file,value);}
        try(DataOutputStream file=binary(dir,"source-"+fs+".bin")){for(int c=0;c<2;c++)for(int a=0;a<2;a++)put(file,new C(a==c?.5:0,0).sub(net.val(volts[a],m.n+c)).scale(.02));}
        for(int a=0;a<2;a++){
          C current=new C(.5,0).sub(net.val(volts[a],m.n+a)).scale(.02);double power=.25*current.r,sum=0;for(int k=0;k<6;k++)sum+=loss[k][a][a].r;
          worstPower=Math.max(worstPower,Math.abs(sum-power)/Math.max(Math.abs(power),1e-30));
          C balance=new C(0,0);double magnitude=0;for(Contact c:net.contacts){C value=net.edgeCurrent(c.edge,volts[a]);balance=balance.add(value);magnitude+=value.abs();}
          worstCurrent=Math.max(worstCurrent,balance.abs()/Math.max(magnitude,1e-30));worstInterface=Math.max(worstInterface,net.interfaceContinuity(volts[a]));
        }
        System.out.printf("WHOLE_LAYER_SC4_CHECK f=%s cells=%d channels=2 completed_RHS=%d residual=%.3g power=%.3g current=%.3g shared_interface=%.3g%n",fs,m.n,rhsCompleted,worstResidual,worstPower,worstCurrent,worstInterface);
      }
      audit.println("]}");
    }
    require(rhsCompleted==8&&Double.isFinite(worstResidual)&&Double.isFinite(worstPower)&&Double.isFinite(worstCurrent)&&Double.isFinite(worstArea)&&Double.isFinite(worstInterface),"Finite completed eight-RHS receipt required");
    require(worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7,"Frozen five native conservation gates failed");
    parentGuard(args,configBytes,false);
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":2,\"cells\":%d,\"h_xy_mm\":0.625,\"sc_cells\":4,\"new_native_RHS\":8,\"new_native_conditions\":1,\"interface_check_scope\":\"shared-flux self consistency, NOT independent interface accuracy\",\"material_calibrated\":false}%n",worstResidual,worstPower,worstCurrent,worstArea,worstInterface,m.n);
    }
    writeMetadata(dir,m,p,configHash(configBytes));new File(dir,"BASIS_COMPLETE").createNewFile();
  }
}
