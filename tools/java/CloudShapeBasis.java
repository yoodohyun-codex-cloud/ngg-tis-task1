import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

/** New-environment execution adapter; frozen numerical source remains untouched.
 * The mesh, operator, solve, field reconstruction and exports are inherited from
 * SelectivityShapeBasis. Only the explicit controller/path/lock contract changes.
 */
public class CloudShapeBasis extends SelectivityShapeBasis {
  // Pure path contract, separated so invalid-path fixtures need no process or PDE.
  static String cloudPathsGuard(Path repo,Path run,Path config,Path basis)throws Exception{
    require(run.isAbsolute()&&run.equals(run.normalize())&&run.equals(run.toRealPath())&&
      Files.isDirectory(run,LinkOption.NOFOLLOW_LINKS)&&
      run.getParent().equals(repo.resolve("data-native").toRealPath()),
      "Run must be a new direct directory under repository data-native; symlink runs forbidden");
    Path bases=run.resolve("bases"),configs=run.resolve("configs");
    require(Files.isDirectory(bases,LinkOption.NOFOLLOW_LINKS)&&Files.isDirectory(configs,LinkOption.NOFOLLOW_LINKS),
      "Run bases/configs must be regular directories");
    require(config.isAbsolute()&&config.equals(config.normalize())&&basis.isAbsolute()&&basis.equals(basis.normalize()),
      "Config and basis must use normalized absolute paths");
    String condition=basis.getFileName().toString();
    require(condition.matches("[A-Za-z0-9][A-Za-z0-9_.-]*"),"Invalid condition ID");
    require(basis.equals(bases.resolve(condition))&&!Files.exists(basis,LinkOption.NOFOLLOW_LINKS),
      "Basis output must be the absent run/bases/condition path");
    require(config.equals(configs.resolve(condition+".properties"))&&
      Files.isRegularFile(config,LinkOption.NOFOLLOW_LINKS),
      "Config must be regular run/configs/condition.properties");
    return condition;
  }

  static void cloudParentGuard(String[] args, byte[] configBytes)throws Exception{
    require(args.length==5&&args[0].equals("--execute-parent"),
      "Actual solve requires --execute-parent PID startticks config basis-dir");
    require(args[1].matches("[1-9][0-9]*")&&args[2].matches("[1-9][0-9]*"),"Invalid parent PID/startticks");
    long pid=Long.parseLong(args[1]),ticks=Long.parseLong(args[2]);
    parentIdentity(pid,ticks);
    List<String> argv=processArguments(pid);int script=-1,execute=-1,output=-1;
    for(int i=0;i<argv.size();i++){
      String arg=argv.get(i);
      if(Paths.get(arg).getFileName()!=null&&Paths.get(arg).getFileName().toString().equals("task1_cloud_batch.py")){
        require(script<0,"Repeated parent executor script");script=i;
      }
      if(arg.equals("--execute")){require(execute<0,"Repeated parent execute flag");execute=i;}
      if(arg.equals("--output")){require(output<0,"Repeated parent output flag");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),
      "Parent must be task1_cloud_batch.py --execute --output run");
    Path cwd=Paths.get("/proc",Long.toString(pid),"cwd").toRealPath();
    Path scriptPath=cwd.resolve(argv.get(script)).toRealPath();
    require(Files.isRegularFile(scriptPath,LinkOption.NOFOLLOW_LINKS),"Parent executor must be a regular file");
    Path tools=scriptPath.getParent(),repo=tools==null?null:tools.getParent();
    require(repo!=null&&tools.getFileName().toString().equals("tools")&&
      scriptPath.equals(repo.resolve("tools/task1_cloud_batch.py").toRealPath()),
      "Parent executor must be repository tools/task1_cloud_batch.py");
    Path rawRun=cwd.resolve(argv.get(output+1)).toAbsolutePath().normalize();
    Path run=rawRun;
    Path basis=Paths.get(args[4]).toAbsolutePath().normalize();
    Path config=Paths.get(args[3]).toAbsolutePath().normalize();
    String condition=cloudPathsGuard(repo,run,config,basis);
    runMarkers(run);
    Path controller=run.resolve("controller.json");
    require(Files.isRegularFile(controller,LinkOption.NOFOLLOW_LINKS),"Missing regular controller.json");
    Map<String,String> fields=new ControllerJson(Files.readString(controller,StandardCharsets.UTF_8)).fields();
    require(controllerString(fields,"status").equals("running")&&
      controllerString(fields,"current_case").equals(condition),"Controller status/current_case mismatch");
    require(controllerLong(fields,"pid")==pid&&controllerLong(fields,"proc_start_ticks")==ticks,
      "Controller parent identity mismatch");
    require(controllerString(fields,"current_config_sha256").equals(configHash(configBytes)),
      "Controller/config SHA256 mismatch");
    parentOwnsLock(pid,repo.resolve(".task1-execution.lock"));
    runMarkers(run);parentIdentity(pid,ticks);
  }

  static void wrapperReceipt(File dir)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"runtime-wrapper.json"),"UTF-8")){
      out.println("{\"schema_version\":1,\"runtime_wrapper_class\":\"CloudShapeBasis\",\"numerical_base_class\":\"SelectivityShapeBasis\",\"guard\":\"tools/task1_cloud_batch.py direct parent; PID/startticks/config SHA; repository global POSIX lock; new data-native run\",\"numerical_operator_modified\":false,\"metadata_exporter_identity\":\"inherited SelectivityShapeBasis contract\",\"original_sources_modified\":false}");
    }
  }

  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestSelectivity();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only exact registered cloud parent execution or --selftest");
    byte[] configBytes=registeredConfig(args[3]);cloudParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    require(p.getProperty("frequencies").equals("3000,3030,9000,9090"),"Fixed carrier/harmonic set");
    int channels=Integer.parseInt(p.getProperty("channels")),sc=Integer.parseInt(p.getProperty("validation.sc_cells"));
    String[] bc=p.getProperty("bulk.counts").split(",");int[] bulk=new int[3];for(int k=0;k<3;k++)bulk[k]=Integer.parseInt(bc[k]);
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    List<double[]> patches=mask(p);ValidationMesh m=new ValidationMesh(number(p,"h_mm"),sc,bulk);
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    wrapperReceipt(dir);
    try(PrintWriter grid=textZipped(dir,"grid.csv")){
      grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int k=0;k<m.n;k++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[k]*1000,m.y[k]*1000,m.z[m.iz[k]]*1000,m.layer[m.iz[k]],m.h*m.h*m.dz[m.iz[k]]);
    }
    double worstResidual=0,worstPower=0,worstCurrent=0,worstArea=0,worstInterface=0;
    for(String fs:p.getProperty("frequencies").split(",")){
      ShapeNet net=new ShapeNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),channels,Double.parseDouble(fs),patches);
      double[] areas=new double[2*channels];for(Contact c:net.contacts)areas[c.pad]+=c.edge.area;
      for(int e=0;e<areas.length;e++){double expected=number(p,"pad."+e+".represented_area_m2");require(Double.isFinite(expected)&&expected>0,"Expected area must be positive finite");worstArea=Math.max(worstArea,Math.abs(areas[e]/expected-1));}
      require(Double.isFinite(worstArea)&&worstArea<=1e-10,"Physical pad area mismatch before solve");
      double[][] volts=new double[channels][];
      try(DataOutputStream fields=zipped(dir,"field-"+fs+".bin")){
        for(int a=0;a<channels;a++){volts[a]=net.solve(a);worstResidual=Math.max(worstResidual,net.residual);for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);}
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
      System.out.printf("SELECTIVITY f=%s h=%s cells=%d residual=%.3g power=%.3g current=%.3g interface=%.3g%n",fs,p.getProperty("h_mm"),m.n,worstResidual,worstPower,worstCurrent,worstInterface);
    }
    require(Double.isFinite(worstResidual)&&Double.isFinite(worstPower)&&Double.isFinite(worstCurrent)&&Double.isFinite(worstArea)&&Double.isFinite(worstInterface),"Nonfinite validation");
    require(worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7,"Numerical conservation gate failed");
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.17g,\"max_power_error\":%.17g,\"max_current_error\":%.17g,\"max_area_relative_error\":%.17g,\"max_interface_normal_current_relative_error\":%.17g,\"channels\":%d,\"cells\":%d,\"h_xy_mm\":%.17g,\"sc_cells\":%d}%n",worstResidual,worstPower,worstCurrent,worstArea,worstInterface,channels,m.n,m.h*1000,sc);
    }
    metadata(dir,m,p,channels,configHash(configBytes));new File(dir,"BASIS_COMPLETE").createNewFile();
  }
}
