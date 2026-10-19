import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Separate preregistered fixed-mesh coating/Rs comparison; private classpath only.
 * Original numerical operations and all transfer/native outputs are preserved.
 * Potential is exported from each already solved voltage vector, with no extra
 * solve. Coating/contact, full3D and physiological convergence remain held.
 * This is not an activation model or a safety certificate.
 */
public class RsWindowTisBasis extends ExploreBasis {
  static final int MAX_CELLS=800000;
  static final String FREQUENCIES="3000,3030,9000,9090";
  // Active preparation 124509Z manifest-v2 236af268... / preregistration-v2 d0f15e16....
  // Nine exact physical inputs, ten semantic slots; the 50nm input is reuse-only.
  // This whitelist is checked before parsing, mesh allocation or output creation.
  static final Set<String> ALLOWED_CONFIG_SHA256=Collections.unmodifiableSet(new HashSet<String>(Arrays.asList(
    "6e69afb9e0a8bb8b278355ab713d493b1383742191fc9304d13d7e5ab4640ad5",
    "90d2a721c173fdb753ae275166cb8044453176b459d4a35ab711b93cf16c8ad9",
    "ebd3fa7a62ceeb9e769a32c3e9217ede10548d0b31059cab09287684d892f773",
    "a7f792fe5ad98cfa87f526bbdc3161bcdeaf1adae2ad724f0a2a477b0eca57e7",
    "251e3ea187362b0db7ac7f8819c6defef7b1d1114f50549034d04caf8ae0017d",
    "5a891a6e4d5c5de89b9de6a718b7c6832631e123d901860149c630cb08e0f4d7",
    "8c5ebc6bca4ee3accf6f7547aee0a9e18374dbff1a5438fb6e7fefba3ec52860",
    "b548a73396aa34fb2c0bb1a2f646d7b1ddca39d99d748db84e3b12be82274731",
    "c09e6882810533686e051f8099b7f12fb83feab639267eac8d36d45556c0e5a9"
  )));
  static final Map<String,String> NEW_SOLVE_CONFIG_SHA256;
  static {
    Map<String,String> inputs=new HashMap<String,String>();
    inputs.put("coat000-f0500-minusRs","6e69afb9e0a8bb8b278355ab713d493b1383742191fc9304d13d7e5ab4640ad5");
    inputs.put("coat010-f0500-minusRs","ebd3fa7a62ceeb9e769a32c3e9217ede10548d0b31059cab09287684d892f773");
    inputs.put("coat030-f0500-minusRs","251e3ea187362b0db7ac7f8819c6defef7b1d1114f50549034d04caf8ae0017d");
    inputs.put("coat100-f0500-minusRs","b548a73396aa34fb2c0bb1a2f646d7b1ddca39d99d748db84e3b12be82274731");
    inputs.put("coat000-f2000-minusRs","90d2a721c173fdb753ae275166cb8044453176b459d4a35ab711b93cf16c8ad9");
    inputs.put("coat010-f2000-minusRs","a7f792fe5ad98cfa87f526bbdc3161bcdeaf1adae2ad724f0a2a477b0eca57e7");
    inputs.put("coat030-f2000-minusRs","5a891a6e4d5c5de89b9de6a718b7c6832631e123d901860149c630cb08e0f4d7");
    inputs.put("coat100-f2000-minusRs","c09e6882810533686e051f8099b7f12fb83feab639267eac8d36d45556c0e5a9");
    NEW_SOLVE_CONFIG_SHA256=Collections.unmodifiableMap(inputs);
  }

  static String configHash(byte[] bytes)throws Exception{
    byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);
    StringBuilder result=new StringBuilder();
    for(byte value:digest){int b=value&255;if(b<16)result.append('0');result.append(Integer.toHexString(b));}
    return result.toString();
  }
  static byte[] registeredConfig(String filename)throws Exception{
    byte[] bytes=Files.readAllBytes(Paths.get(filename));
    if(!ALLOWED_CONFIG_SHA256.contains(configHash(bytes)))throw new IllegalArgumentException("Input is not one of the nine preregistered Rs-window config SHA256 values");
    return bytes;
  }

  // Controller parsing is deliberately independent of the numerical operator.
  // Preserve top-level field identity even when nested objects also use status/pid.
  static class ControllerJson {
    final String text;int at=0;
    ControllerJson(String text){this.text=text;}
    void space(){while(at<text.length()&&Character.isWhitespace(text.charAt(at)))at++;}
    void take(char expected){space();require(at<text.length()&&text.charAt(at++)==expected,"Malformed controller JSON");}
    String string(){
      take('"');StringBuilder result=new StringBuilder();boolean closed=false;
      while(at<text.length()){
        char c=text.charAt(at++);if(c=='"'){closed=true;break;}
        require(c>=32,"Control character in controller JSON");
        if(c=='\\'){
          require(at<text.length(),"Incomplete controller escape");char e=text.charAt(at++);
          switch(e){
            case '"':case '\\':case '/':c=e;break;
            case 'b':c='\b';break;case 'f':c='\f';break;case 'n':c='\n';break;
            case 'r':c='\r';break;case 't':c='\t';break;
            case 'u':
              require(at+4<=text.length(),"Incomplete controller Unicode escape");
              String hex=text.substring(at,at+4);require(hex.matches("[0-9a-fA-F]{4}"),"Invalid controller Unicode escape");
              c=(char)Integer.parseInt(hex,16);at+=4;break;
            default:throw new IllegalStateException("Invalid controller escape");
          }
        }
        result.append(c);
      }
      require(closed,"Unterminated controller string");return result.toString();
    }
    void value(int depth){
      require(depth<64,"Controller JSON nesting limit");space();require(at<text.length(),"Missing controller value");char c=text.charAt(at);
      if(c=='"'){string();return;}
      if(c=='{'||c=='['){
        at++;space();char end=c=='{'?'}':']';if(at<text.length()&&text.charAt(at)==end){at++;return;}
        while(true){
          if(c=='{'){string();take(':');}value(depth+1);space();require(at<text.length(),"Incomplete controller object");
          char separator=text.charAt(at++);if(separator==end)return;require(separator==',',"Malformed controller separator");
        }
      }
      int start=at;while(at<text.length()&&",]} \t\r\n".indexOf(text.charAt(at))<0)at++;
      String token=text.substring(start,at);
      require(token.equals("true")||token.equals("false")||token.equals("null")||token.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?"),"Invalid controller scalar");
    }
    Map<String,String> fields(){
      Map<String,String> fields=new HashMap<String,String>();take('{');space();
      if(at<text.length()&&text.charAt(at)=='}'){at++;space();require(at==text.length(),"Trailing controller JSON");return fields;}
      while(true){
        String key=string();take(':');space();int start=at;value(0);
        require(!fields.containsKey(key),"Duplicate controller field: "+key);fields.put(key,text.substring(start,at));
        space();require(at<text.length(),"Incomplete controller JSON");char separator=text.charAt(at++);
        if(separator=='}')break;require(separator==',',"Malformed controller object");
      }
      space();require(at==text.length(),"Trailing controller JSON");return fields;
    }
  }
  static String controllerString(Map<String,String> fields,String key){
    require(fields.containsKey(key),"Missing controller field: "+key);
    ControllerJson value=new ControllerJson(fields.get(key));String result=value.string();value.space();
    require(value.at==value.text.length(),"Invalid controller string: "+key);return result;
  }
  static long controllerLong(Map<String,String> fields,String key){
    String value=fields.get(key);require(value!=null&&value.matches("[1-9][0-9]*"),"Invalid controller integer: "+key);return Long.parseLong(value);
  }
  static long processStartTicks(long pid)throws Exception{
    String stat=Files.readString(Paths.get("/proc",Long.toString(pid),"stat"),StandardCharsets.UTF_8);
    int close=stat.lastIndexOf(')');require(close>0,"Malformed parent /proc stat");
    String[] fields=stat.substring(close+1).trim().split("\\s+");
    require(fields.length>19,"Incomplete parent /proc stat");return Long.parseLong(fields[19]);
  }
  static void parentIdentity(long pid,long ticks)throws Exception{
    ProcessHandle parent=ProcessHandle.current().parent().orElseThrow(()->new IllegalStateException("Missing direct Python parent"));
    require(parent.pid()==pid&&parent.isAlive()&&processStartTicks(pid)==ticks,"Direct parent PID/startticks mismatch");
  }
  static List<String> processArguments(long pid)throws Exception{
    byte[] bytes=Files.readAllBytes(Paths.get("/proc",Long.toString(pid),"cmdline"));List<String> result=new ArrayList<String>();
    int start=0;for(int i=0;i<bytes.length;i++)if(bytes[i]==0){result.add(new String(bytes,start,i-start,StandardCharsets.UTF_8));start=i+1;}
    require(start==bytes.length&&!result.isEmpty(),"Malformed parent command line");return result;
  }
  static void runMarkers(Path run){
    for(String name:new String[]{"STOP","needs_attention","needs_physical_validation"})
      require(!Files.exists(run.resolve(name),LinkOption.NOFOLLOW_LINKS),"New run blocked by "+name);
  }
  static void parentOwnsLock(long pid,Path lock)throws Exception{
    require(Files.isRegularFile(lock,LinkOption.NOFOLLOW_LINKS),"Missing regular execution lock");boolean owned=false;
    // Python holds BOTH flock and lockf; FileChannel.tryLock checks the latter.
    // fdinfo ties the POSIX owner to this exact inode, without guessing dev_t.
    try(DirectoryStream<Path> fds=Files.newDirectoryStream(Paths.get("/proc",Long.toString(pid),"fd"))){
      for(Path fd:fds){
        try{
          if(!Files.isSameFile(lock,fd))continue;
          for(String line:Files.readAllLines(Paths.get("/proc",Long.toString(pid),"fdinfo",fd.getFileName().toString()),StandardCharsets.UTF_8)){
            String[] parts=line.trim().split("\\s+");
            if(parts.length==9&&parts[0].equals("lock:")&&parts[2].equals("POSIX")&&parts[3].equals("ADVISORY")
              &&parts[4].equals("WRITE")&&parts[5].equals(Long.toString(pid))&&parts[7].equals("0")&&parts[8].equals("EOF"))owned=true;
          }
        }catch(IOException vanished){/* An unrelated parent descriptor can close during inspection. */}
      }
    }
    require(owned,"Parent must own the full-file POSIX execution lock (fcntl.lockf)");
    try(FileChannel channel=FileChannel.open(lock,StandardOpenOption.READ,StandardOpenOption.WRITE)){
      FileLock acquired=channel.tryLock();
      if(acquired!=null){acquired.release();throw new IllegalStateException("Execution lock is not held by parent");}
    }
  }
  static void executeParentGuard(String[] args,byte[] configBytes)throws Exception{
    require(args.length==5&&args[0].equals("--execute-parent"),"Actual solve requires --execute-parent PID startticks config basis-dir");
    require(args[1].matches("[1-9][0-9]*")&&args[2].matches("[1-9][0-9]*"),"Invalid parent PID/startticks");
    long pid=Long.parseLong(args[1]),ticks=Long.parseLong(args[2]);parentIdentity(pid,ticks);
    List<String> argv=processArguments(pid);int script=-1,execute=-1,output=-1;
    for(int i=0;i<argv.size();i++){
      String arg=argv.get(i);
      if(arg.endsWith("rs_window_tis_validation.py")&&Paths.get(arg).getFileName().toString().equals("rs_window_tis_validation.py")){
        require(script<0,"Repeated parent executor script");script=i;
      }
      if(arg.equals("--execute")){require(execute<0,"Repeated parent execute flag");execute=i;}
      if(arg.equals("--output")){require(output<0,"Repeated parent output flag");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),"Parent must be rs_window_tis_validation.py --execute --output run");
    Path parentCwd=Paths.get("/proc",Long.toString(pid),"cwd").toRealPath();
    Path run=parentCwd.resolve(argv.get(output+1)).toRealPath();require(Files.isDirectory(run),"Parent output is not a run directory");runMarkers(run);
    Path scriptPath=parentCwd.resolve(argv.get(script)).toRealPath();
    require(run.getParent()!=null&&run.getParent().getParent()!=null,"Invalid parent output run path");
    Path expectedScript=run.getParent().getParent().resolve("rs_window_tis_validation.py").toRealPath();
    require(Files.isRegularFile(scriptPath)&&scriptPath.equals(expectedScript),"Parent executor must be the exact rs_window_tis_validation.py beside runs");
    Path basis=Paths.get(args[4]).toAbsolutePath().normalize();String condition=basis.getFileName().toString();
    require(NEW_SOLVE_CONFIG_SHA256.containsKey(condition),"Condition is not one of eight new solves; 50nm aliases are reuse-only");
    require(configHash(configBytes).equals(NEW_SOLVE_CONFIG_SHA256.get(condition)),"Condition/config byte SHA256 mismatch");
    Path bases=run.resolve("bases"),configs=run.resolve("configs");
    require(Files.isDirectory(bases,LinkOption.NOFOLLOW_LINKS)&&Files.isDirectory(configs,LinkOption.NOFOLLOW_LINKS),"Run bases/configs must be regular directories");
    require(basis.equals(bases.resolve(condition))&&!Files.exists(basis,LinkOption.NOFOLLOW_LINKS),"Basis output must be the new run/bases/condition path");
    Path config=Paths.get(args[3]).toAbsolutePath().normalize();
    require(config.equals(configs.resolve(condition+".properties"))&&Files.isRegularFile(config,LinkOption.NOFOLLOW_LINKS),"Config must be run/configs/condition.properties");
    Path controller=run.resolve("controller.json");require(Files.isRegularFile(controller,LinkOption.NOFOLLOW_LINKS),"Missing regular controller.json");
    Map<String,String> fields=new ControllerJson(Files.readString(controller,StandardCharsets.UTF_8)).fields();
    require(controllerString(fields,"status").equals("running")&&controllerString(fields,"current_case").equals(condition),"Controller status/current_case mismatch");
    require(controllerLong(fields,"pid")==pid&&controllerLong(fields,"proc_start_ticks")==ticks,"Controller parent identity mismatch");
    parentOwnsLock(pid,run.resolve(".execution.lock"));runMarkers(run);parentIdentity(pid,ticks);
  }
  static void meshMetadata(File dir,ValidationMesh mesh,String configSha)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"validation_native\",\"exporter_class\":\"RsWindowTisBasis\",\"config_sha256\":\"%s\",",configSha);
      out.printf("\"field_reconstruction\":\"finite_volume_half_face_flux\",\"h_xy_mm\":%.17g,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":2,",mesh.h*1000,mesh.nx,mesh.nz,mesh.n);
      out.printf("\"sc_cells\":%d,\"layer_counts\":[%d,14,14,40],\"bulk_layer_counts\":[14,14,40],\"frequencies_Hz\":[3000,3030,9000,9090],",mesh.scCells,mesh.scCells);
      out.print("\"coordinate_system\":{\"unit\":\"mm\",\"surface_z_mm\":0.0,\"depth_axis\":\"+z\",\"x_y_axes\":\"local phantom axes; no anatomical registration\"},");
      out.print("\"cell_order\":\"grid.csv rows, masked cylinder, z then y then x\",\"grid_filename\":\"grid.csv\",");
      out.print("\"layers\":[{\"id\":0,\"name\":\"sc\",\"z_min_mm\":0.0,\"z_max_mm\":0.1},{\"id\":1,\"name\":\"dermis\",\"z_min_mm\":0.1,\"z_max_mm\":5.1},{\"id\":2,\"name\":\"fat\",\"z_min_mm\":5.1,\"z_max_mm\":10.1},{\"id\":3,\"name\":\"muscle\",\"z_min_mm\":10.1,\"z_max_mm\":25.1}],");
      out.print("\"z_faces_mm\":[");
      for(int k=0;k<mesh.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(mesh.z[k]-mesh.dz[k]/2)*1000);}
      out.printf(",%.17g],",(mesh.z[mesh.nz-1]+mesh.dz[mesh.nz-1]/2)*1000);
      out.print("\"potential_storage\":{\"filename_template\":\"potential-{frequency_Hz}.bin\",\"dtype\":\"<c16\",\"shape\":[2,"+mesh.n+"],\"axis_order\":[\"basis_channel\",\"grid_cell\"],\"complex_encoding\":\"little-endian float64 real,imaginary pairs\",\"reference\":\"common return GND=0V\"},");
      out.print("\"basis_normalization\":{\"source_peak_V\":0.5,\"source_Vpp\":1.0,\"source_resistance_ohm\":50.0,\"phasor_exponent\":\"+jomega_t\"},\"potential_export_additional_solves\":0,\"fixed_mesh_coating_Rs_comparison_only\":true,\"coating_Rs_convergence_status\":\"held\",\"full_3D_convergence_status\":\"held\"}\n");
    }
  }

  static class ValidationMesh extends Mesh {
    final int scCells;
    ValidationMesh(double hm,int sc){
      // Avoid allocating the default, h-dependent bulk mesh before replacing it.
      super(2.5);
      if(!(hm>0)||!Double.isFinite(hm)||(sc!=2&&sc!=4&&sc!=8))throw new IllegalArgumentException("Invalid diagnostic mesh");
      scCells=sc;h=hm/1000;nx=(int)Math.round(.05/h);
      if(nx<2||nx>120||Math.abs(nx*h-.05)>1e-12)throw new IllegalArgumentException("XY must tile 50 mm exactly");
      int[] counts={sc,14,14,40};double[] thick={.0001,.005,.005,.015};
      int nxy=0;for(int j=0;j<nx;j++)for(int i=0;i<nx;i++){
        double a=-.025+(i+.5)*h,b=-.025+(j+.5)*h;if(a*a+b*b<.025*.025)nxy++;
      }
      nz=sc+68;if((long)nxy*nz>MAX_CELLS)throw new IllegalArgumentException("Diagnostic cell limit");
      z=new double[nz];dz=new double[nz];layer=new int[nz];double zz=0;int at=0;
      for(int l=0;l<4;l++)for(int k=0;k<counts[l];k++){
        dz[at]=thick[l]/counts[l];z[at]=zz+dz[at]/2;zz+=dz[at];layer[at++]=l;
      }
      n=nxy*nz;id=new int[nz][nx][nx];ix=new int[n];iy=new int[n];iz=new int[n];x=new double[n];y=new double[n];
      int p=0;for(int k=0;k<nz;k++)for(int j=0;j<nx;j++)for(int i=0;i<nx;i++){
        double a=-.025+(i+.5)*h,b=-.025+(j+.5)*h;id[k][j][i]=-1;
        if(a*a+b*b<.025*.025){id[k][j][i]=p;ix[p]=i;iy[p]=j;iz[p]=k;x[p]=a;y[p]=b;p++;}
      }
      if(p!=n)throw new IllegalStateException("Mesh count mismatch");
    }
  }

  static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
  static void selftestDiagnostic(){
    Mesh old=new Mesh(.625);ValidationMesh same=new ValidationMesh(.625,2);
    require(old.n==same.n&&old.nz==same.nz&&old.nx==same.nx,"Default mesh dimensions");
    require(Arrays.equals(old.x,same.x)&&Arrays.equals(old.y,same.y)&&Arrays.equals(old.z,same.z)
      &&Arrays.equals(old.dz,same.dz)&&Arrays.equals(old.layer,same.layer)
      &&Arrays.equals(old.ix,same.ix)&&Arrays.equals(old.iy,same.iy)&&Arrays.equals(old.iz,same.iz),"Default mesh arrays differ");
    for(int k=0;k<old.nz;k++)for(int j=0;j<old.nx;j++)require(Arrays.equals(old.id[k][j],same.id[k][j]),"Default mesh mask differs");
    old=null;same=null;
    for(int sc:new int[]{2,4,8}){
      ValidationMesh mesh=new ValidationMesh(.625,sc);double[] totals=new double[4];
      for(int k=0;k<mesh.nz;k++)totals[mesh.layer[k]]+=mesh.dz[k];
      double[] expected={.0001,.005,.005,.015};
      for(int l=0;l<4;l++)require(Math.abs(totals[l]-expected[l])<1e-14,"Layer thickness changed");
      require(mesh.n==5024*(68+sc),"Independent SC cell count");
      mesh=null;
      // Small independent complex series circuit, with the SC split into sc pieces.
      // Only a few unknowns are solved; no cylindrical PDE is solved here.
      Mesh dummy=new Mesh(2.5);Net net=new Net(dummy,new Scenario("circuit",.01,.001,1),layouts().get(0),3000);
      int nodes=sc+3;net.edges.clear();dummy.n=nodes;net.N=nodes+2;
      net.dr=new double[net.N];net.di=new double[net.N];
      C gamma=new C(.0002,2*Math.PI*3000*EPS0*110000),contact=new C(10,-22),bulk=new C(300,-40);
      C segment=new C(.0001/sc/1e-4,0).div(gamma),total=contact.add(bulk).add(segment.scale(sc));
      net.add(nodes,0,new C(1,0).div(contact),0,1);
      for(int k=0;k<sc;k++)net.add(k,k+1,new C(1,0).div(segment),0,1);
      net.add(sc,-1,new C(1,0).div(bulk),0,1);
      // One unused tissue node is grounded to keep the tiny test nonsingular.
      net.add(sc+1,-1,new C(1,0),0,1);net.add(sc+2,-1,new C(1,0),0,1);
      net.dr[nodes]+=.02;net.dr[nodes+1]+=.02;
      double[] voltage=net.solve(0);C current=new C(.5,0).sub(net.val(voltage,nodes)).scale(.02);
      C exact=new C(.5,0).div(total.add(new C(50,0)));
      require(current.sub(exact).abs()/exact.abs()<2e-7,"SC series circuit analytic mismatch");
    }
    System.out.println("VALIDATION3K_SELFTEST default mesh identity, fixed layer thickness and independent 3kHz complex SC circuit passed");
  }

  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestDiagnostic();return;}
    if(args.length==2&&args[0].equals("--validate-config")){
      byte[] bytes=registeredConfig(args[1]);
      System.out.println("VALIDATION3K_CONFIG_OK "+configHash(bytes));return;
    }
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("RsWindowTisBasis --execute-parent pythonPID startticks config.properties new-basis-folder | --validate-config config.properties | --selftest");
    byte[] configBytes=registeredConfig(args[3]);
    executeParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    double h=number(p,"h_mm"),size=number(p,"size_mm")/1000;int channels=(int)number(p,"channels");
    if(channels!=2)throw new IllegalArgumentException("Diagnostic fixes two outputs");
    int sc=Integer.parseInt(p.getProperty("validation.sc_cells","2"));
    if(!p.getProperty("frequencies").equals(FREQUENCIES))throw new IllegalArgumentException("Diagnostic frequencies changed");
    double[][] xy=new double[4][2];for(int e=0;e<4;e++){xy[e][0]=number(p,"pad."+e+".x_mm")/1000;xy[e][1]=number(p,"pad."+e+".y_mm")/1000;}
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    ValidationMesh m=new ValidationMesh(h,sc);
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
    try(PrintWriter grid=new PrintWriter(new File(dir,"grid.csv"),"UTF-8")){
      grid.println("x_mm,y_mm,z_mm,layer,volume_m3");for(int i=0;i<m.n;i++)grid.printf("%.12g,%.12g,%.12g,%d,%.12g%n",m.x[i]*1000,m.y[i]*1000,m.z[m.iz[i]]*1000,m.layer[m.iz[i]],m.h*m.h*m.dz[m.iz[i]]);
    }
    double worstResidual=0,worstPower=0,worstCurrent=0,worstArea=0;
    for(String fs:p.getProperty("frequencies").split(",")){
      double f=Double.parseDouble(fs);GNet net=new GNet(m,new Boundary(number(p,"z."+fs+".re"),number(p,"z."+fs+".im")),xy,size,channels,f);
      double[] area=new double[4];for(Contact c:net.contacts)area[c.pad]+=c.edge.area;
      for(double a:area)worstArea=Math.max(worstArea,Math.abs(a/(size*size)-1));
      if(worstArea>1e-10)throw new IllegalStateException("Physical pad area changed");
      double[][] volts=new double[channels][];
      try(DataOutputStream fields=binary(dir,"field-"+fs+".bin")){
        for(int a=0;a<channels;a++){
          volts[a]=net.solve(a);worstResidual=Math.max(worstResidual,net.residual);
          for(double[] row:net.field(volts[a]))for(double value:row)put(fields,value);
        }
      }
      // Native tissue potential from the existing solved vectors: no new solve.
      try(DataOutputStream potential=binary(dir,"potential-"+fs+".bin")){
        for(int a=0;a<channels;a++)for(int cell=0;cell<m.n;cell++)put(potential,net.val(volts[a],cell));
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
        worstPower=Math.max(worstPower,Math.abs(sum-power)/Math.max(Math.abs(power),1e-30));
        C balance=new C(0,0);double magnitude=0;
        for(Contact contact:net.contacts){C current=net.edgeCurrent(contact.edge,volts[a]);balance=balance.add(current);magnitude+=current.abs();}
        worstCurrent=Math.max(worstCurrent,balance.abs()/Math.max(magnitude,1e-30));
      }
      System.out.printf("VALIDATION f=%.0f h=%.12g SC=%d cells=%d residual=%.3g power=%.3g current=%.3g%n",f,h,sc,m.n,worstResidual,worstPower,worstCurrent);
    }
    require(Double.isFinite(worstResidual)&&Double.isFinite(worstPower)&&Double.isFinite(worstCurrent),"Nonfinite validation");
    require(worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10,"Numerical conservation gate failed");
    try(PrintWriter out=new PrintWriter(new File(dir,"validation.json"),"UTF-8")){
      out.printf("{\"max_residual\":%.16g,\"max_power_error\":%.16g,\"max_current_error\":%.16g,\"max_area_relative_error\":%.16g,\"channels\":2,\"cells\":%d,\"h_xy_mm\":%.16g,\"sc_cells\":%d,\"bulk_layer_counts\":[14,14,40]}%n",worstResidual,worstPower,worstCurrent,worstArea,m.n,h,sc);
    }
    meshMetadata(dir,m,configHash(configBytes));
    new File(dir,"BASIS_COMPLETE").createNewFile();
  }
}
