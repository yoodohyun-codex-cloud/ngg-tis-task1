import java.io.*;
import java.util.*;
import java.nio.file.*;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.zip.GZIPOutputStream;
/** Finite fixed-phantom shape comparison. Original bulk operator/common GND/50ohm are retained.
 * New fractional contact faces use a preregistered polygon mask and cell-face-averaged surface E.
 * Native peak complex E/phi are exported once from solved vectors; gzip is lossless storage only.
 */
public class SelectivityShapeBasis extends ExploreBasis {
  static final int MAX_CELLS=800000;
  static String configHash(byte[] bytes)throws Exception{
    byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);
    StringBuilder result=new StringBuilder();
    for(byte value:digest){int b=value&255;if(b<16)result.append('0');result.append(Integer.toHexString(b));}
    return result.toString();
  }
  static byte[] registeredConfig(String filename)throws Exception{return Files.readAllBytes(Paths.get(filename));}

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
      if(arg.endsWith("selectivity_design.py")&&Paths.get(arg).getFileName().toString().equals("selectivity_design.py")){
        require(script<0,"Repeated parent executor script");script=i;
      }
      if(arg.equals("--execute")){require(execute<0,"Repeated parent execute flag");execute=i;}
      if(arg.equals("--output")){require(output<0,"Repeated parent output flag");output=i;}
    }
    require(script>=0&&execute>script&&output>script&&output+1<argv.size(),"Parent must be selectivity_design.py --execute --output run");
    Path parentCwd=Paths.get("/proc",Long.toString(pid),"cwd").toRealPath();
    Path run=parentCwd.resolve(argv.get(output+1)).toRealPath();require(Files.isDirectory(run),"Parent output is not a run directory");runMarkers(run);
    Path scriptPath=parentCwd.resolve(argv.get(script)).toRealPath();
    require(run.getParent()!=null&&run.getParent().getParent()!=null,"Invalid parent output run path");
    Path expectedScript=run.getParent().getParent().resolve("selectivity_design.py").toRealPath();
    require(Files.isRegularFile(scriptPath)&&scriptPath.equals(expectedScript),"Parent executor must be the exact selectivity_design.py beside runs");
    Path basis=Paths.get(args[4]).toAbsolutePath().normalize();String condition=basis.getFileName().toString();
    Path bases=run.resolve("bases"),configs=run.resolve("configs");
    require(Files.isDirectory(bases,LinkOption.NOFOLLOW_LINKS)&&Files.isDirectory(configs,LinkOption.NOFOLLOW_LINKS),"Run bases/configs must be regular directories");
    require(basis.equals(bases.resolve(condition))&&!Files.exists(basis,LinkOption.NOFOLLOW_LINKS),"Basis output must be the new run/bases/condition path");
    Path config=Paths.get(args[3]).toAbsolutePath().normalize();
    require(config.equals(configs.resolve(condition+".properties"))&&Files.isRegularFile(config,LinkOption.NOFOLLOW_LINKS),"Config must be run/configs/condition.properties");
    Path controller=run.resolve("controller.json");require(Files.isRegularFile(controller,LinkOption.NOFOLLOW_LINKS),"Missing regular controller.json");
    Map<String,String> fields=new ControllerJson(Files.readString(controller,StandardCharsets.UTF_8)).fields();
    require(controllerString(fields,"status").equals("running")&&controllerString(fields,"current_case").equals(condition),"Controller status/current_case mismatch");
    require(controllerLong(fields,"pid")==pid&&controllerLong(fields,"proc_start_ticks")==ticks,"Controller parent identity mismatch");
    require(controllerString(fields,"current_config_sha256").equals(configHash(configBytes)),"Controller/config SHA256 mismatch");
    parentOwnsLock(pid,run.resolve(".execution.lock"));runMarkers(run);parentIdentity(pid,ticks);
  }
  static class ValidationMesh extends Mesh {
    final int scCells;
    ValidationMesh(double hm,int sc,int[] bulk){
      // Avoid allocating the default, h-dependent bulk mesh before replacing it.
      super(2.5);
      if(!(hm>0)||!Double.isFinite(hm)||(sc!=2&&sc!=4&&sc!=8))throw new IllegalArgumentException("Invalid diagnostic mesh");
      scCells=sc;h=hm/1000;nx=(int)Math.round(.05/h);
      if(nx<2||nx>120||Math.abs(nx*h-.05)>1e-12)throw new IllegalArgumentException("XY must tile 50 mm exactly");
      if(!Arrays.equals(bulk,new int[]{14,14,40})&&!Arrays.equals(bulk,new int[]{18,18,56}))throw new IllegalArgumentException("Unregistered bulk grid");
      int[] counts={sc,bulk[0],bulk[1],bulk[2]};double[] thick={.0001,.005,.005,.015};
      int nxy=0;for(int j=0;j<nx;j++)for(int i=0;i<nx;i++){
        double a=-.025+(i+.5)*h,b=-.025+(j+.5)*h;if(a*a+b*b<.025*.025)nxy++;
      }
      nz=sc+bulk[0]+bulk[1]+bulk[2];if((long)nxy*nz>MAX_CELLS)throw new IllegalArgumentException("Diagnostic cell limit");
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


  static class ShapeNet extends Net {
    final int channels; final List<Contact> contacts=new ArrayList<Contact>();
    ShapeNet(Mesh m,Scenario s,int channels,double f,List<double[]> mask){
      super(m,s,TisSweep.layouts().get(0),f);this.channels=channels;
      N=m.n+channels;edges.clear();dr=new double[N];di=new double[N];
      require(channels==1||channels==2,"Only one or two outputs registered");
      for(int p=0;p<m.n;p++){
        int i=m.ix[p],j=m.iy[p],k=m.iz[p];C ga=gamma[m.layer[k]];
        int q=m.at(i+1,j,k);if(q>=0)add(p,q,ga.scale(m.dz[k]),0,m.h*m.dz[k]);
        q=m.at(i,j+1,k);if(q>=0)add(p,q,ga.scale(m.dz[k]),1,m.h*m.dz[k]);
        q=m.at(i,j,k+1);if(q>=0){C zz=new C(m.dz[k]/2,0).div(ga).add(new C(m.dz[k+1]/2,0).div(gamma[m.layer[k+1]]));add(p,q,new C(m.h*m.h,0).div(zz),2,m.h*m.h);}
      }
      double[] covered=new double[m.n];
      for(double[] row:mask){
        int e=(int)row[0],i=(int)row[1],j=(int)row[2],p=m.at(i,j,0);double area=row[3];
        require(e>=0&&e<2*channels&&p>=0&&Double.isFinite(area)&&area>0&&area<=m.h*m.h*(1+1e-10),"Invalid fractional contact");
        covered[p]+=area;require(covered[p]<=m.h*m.h*(1+1e-10),"Overlapping fractional contacts in one surface face");
        C zz=s.zc(omega).add(new C(m.dz[0]/2,0).div(gamma[0]));
        add(p,e<channels?m.n+e:-1,new C(area,0).div(zz),-1,area);
        contacts.add(new Contact(edges.get(edges.size()-1),e));
      }
      for(int c=0;c<channels;c++)dr[m.n+c]+=.02;
    }
    double[][] field(double[] v){
      double[][] result=new double[m.n][6];
      for(Edge edge:edges){
        C current=edgeCurrent(edge,v);
        if(edge.axis>=0){
          C ea=current.div(gamma[m.layer[m.iz[edge.a]]]).scale(.5/edge.area);
          C eb=current.div(gamma[m.layer[m.iz[edge.b]]]).scale(.5/edge.area);
          result[edge.a][2*edge.axis]+=ea.r;result[edge.a][2*edge.axis+1]+=ea.i;
          result[edge.b][2*edge.axis]+=eb.r;result[edge.b][2*edge.axis+1]+=eb.i;
        }else{
          // Cell-face mean: fractional electrode current is averaged over h^2.
          // Contact J itself remains I/A_overlap, without this averaging.
          C ez=current.div(gamma[0]).scale(-.5/(m.h*m.h));
          result[edge.a][4]+=ez.r;result[edge.a][5]+=ez.i;
        }
      }
      return result;
    }
    double interfaceContinuity(double[] v){
      double difference=0,scale=0;
      for(Edge edge:edges)if(edge.axis==2&&m.layer[m.iz[edge.a]]!=m.layer[m.iz[edge.b]]){
        int ka=m.iz[edge.a],kb=m.iz[edge.b];C current=edgeCurrent(edge,v);
        C face=val(v,edge.a).sub(current.div(gamma[m.layer[ka]]).scale(m.dz[ka]/(2*edge.area)));
        C upper=val(v,edge.a).sub(face).mul(gamma[m.layer[ka]]).scale(2/m.dz[ka]);
        C lower=face.sub(val(v,edge.b)).mul(gamma[m.layer[kb]]).scale(2/m.dz[kb]);
        difference=Math.max(difference,upper.sub(lower).abs());scale=Math.max(scale,Math.max(upper.abs(),lower.abs()));
      }
      return difference/Math.max(scale,1e-30);
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

  static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
  static DataOutputStream zipped(File dir,String name)throws Exception{return new DataOutputStream(new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(new File(dir,name+".gz")),65536),65536));}
  static PrintWriter textZipped(File dir,String name)throws Exception{return new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(new File(dir,name+".gz")),65536),StandardCharsets.UTF_8));}
  static List<double[]> mask(Properties p)throws Exception{
    Path path=Paths.get(p.getProperty("mask.path")).toAbsolutePath();byte[] data=Files.readAllBytes(path);
    require(configHash(data).equals(p.getProperty("mask.sha256")),"Frozen mask SHA differs");
    List<double[]> result=new ArrayList<double[]>();String[] rows=new String(data,StandardCharsets.UTF_8).split("\\R");
    require(rows[0].equals("pad,i,j,area_m2"),"Mask schema differs");
    for(int k=1;k<rows.length;k++){if(rows[k].isBlank())continue;String[] v=rows[k].split(",");require(v.length==4,"Mask row schema");double[] r=new double[4];for(int t=0;t<4;t++){r[t]=Double.parseDouble(v[t]);require(Double.isFinite(r[t]),"Nonfinite mask value");}for(int t=0;t<3;t++)require(r[t]>=0&&r[t]==Math.rint(r[t]),"Mask IDs must be nonnegative integers");require(r[3]>0,"Positive mask area required");result.add(r);}
    return result;
  }
  static void metadata(File dir,ValidationMesh m,Properties p,int channels,String hash)throws Exception{
    try(PrintWriter out=new PrintWriter(new File(dir,"mesh-metadata.json"),"UTF-8")){
      out.printf("{\"schema_version\":1,\"exporter_kind\":\"selectivity_native\",\"exporter_class\":\"SelectivityShapeBasis\",\"config_sha256\":\"%s\",\"h_xy_mm\":%.17g,\"radius_mm\":25.0,\"total_depth_mm\":25.1,\"nx\":%d,\"nz\":%d,\"cells\":%d,\"channels\":%d,",hash,m.h*1000,m.nx,m.nz,m.n,channels);
      out.printf("\"sc_cells\":%d,\"bulk_layer_counts\":[%s],\"frequencies_Hz\":[3000,3030,9000,9090],",m.scCells,p.getProperty("bulk.counts"));
      out.print("\"phasor_convention\":\"peak,+jomega_t\",\"source_peak_V\":0.5,\"source_resistance_ohm\":50.0,\"field_reconstruction\":\"half_face_flux; top contact term averaged over full cell face h^2\",\"storage\":\"lossless gzip of original little-endian Float64/complex128\",\"side_bottom_boundary\":\"insulating no outside faces; fixed 50mm cylinder staircase mask\",\"z_faces_mm\":[");
      for(int k=0;k<m.nz;k++){if(k>0)out.print(',');out.printf("%.17g",(m.z[k]-m.dz[k]/2)*1000);}out.print(",25.1],\"tissue_boundaries_mm\":[0,0.1,5.1,10.1,25.1],\"new_potential_solves\":0}\n");
    }
  }
  static void selftestSelectivity()throws Exception{
    // Independent partial-face capacitor/resistor current must be averaged by h^2 in E.
    ValidationMesh m=new ValidationMesh(1.25,2,new int[]{14,14,40});
    List<double[]> patches=new ArrayList<double[]>();int i=m.nx/2,j=m.nx/2;double area=m.h*m.h*.25;
    patches.add(new double[]{0,i,j,area});patches.add(new double[]{1,i+2,j,area});
    ShapeNet net=new ShapeNet(m,new Boundary(.01,-.02),1,3000,patches);
    double[] v=new double[2*net.N];v[2*m.n]=.5;
    double[][] field=net.field(v);int at=m.at(i,j,0);Edge contact=net.contacts.get(0).edge;
    C expected=net.edgeCurrent(contact,v).div(net.gamma[0]).scale(-.5/(m.h*m.h));
    require(Math.hypot(field[at][4]-expected.r,field[at][5]-expected.i)<1e-12,"Fractional contact field averaging");
    require(Math.abs(net.resistance(contact,0)-new C(m.dz[0]/(2*area),0).div(net.gamma[0]).r)<1e-12,"Partial-face resistance");
    // Original axis-aligned baseline operator/field identity without solving a phantom PDE.
    List<double[]> full=new ArrayList<double[]>();double[][] xy={{-.01,-.01},{.01,.01},{.01,-.01},{-.01,.01}};
    for(int cell=0;cell<m.n;cell++)if(m.iz[cell]==0)for(int e=0;e<4;e++)
      if(Math.abs(m.x[cell]-xy[e][0])<.0075&&Math.abs(m.y[cell]-xy[e][1])<.0075)
        full.add(new double[]{e,m.ix[cell],m.iy[cell],m.h*m.h});
    GNet old=new GNet(m,new Boundary(.01,-.02),xy,.015,2,3000);
    ShapeNet shape=new ShapeNet(m,new Boundary(.01,-.02),2,3000,full);
    double[] input=new double[2*old.N];for(int k=0;k<input.length;k++)input[k]=Math.sin(k*.123)*.3;
    double[] a=old.raw(input),b=shape.raw(input);double delta=0,scale=0;
    for(int k=0;k<a.length;k++){delta=Math.max(delta,Math.abs(a[k]-b[k]));scale=Math.max(scale,Math.abs(a[k]));}
    require(delta/scale<1e-12,"Original baseline operator identity");
    double[][] ea=old.field(input),eb=shape.field(input);delta=0;scale=0;
    for(int k=0;k<m.n;k++)for(int q=0;q<6;q++){delta=Math.max(delta,Math.abs(ea[k][q]-eb[k][q]));scale=Math.max(scale,Math.abs(ea[k][q]));}
    require(delta/scale<1e-12,"Original full-face baseline E identity");
    // Independent small complex series circuit tests amplitude/source and layered current.
    Mesh dummy=new Mesh(2.5);Net tiny=new Net(dummy,new Scenario("circuit",.01,.001,1),layouts().get(0),3000);
    tiny.edges.clear();dummy.n=3;tiny.N=5;tiny.dr=new double[5];tiny.di=new double[5];
    C z1=new C(25,-13),z2=new C(71,-24);tiny.add(3,0,new C(1,0).div(z1),0,1);
    tiny.add(0,-1,new C(1,0).div(z2),0,1);tiny.add(1,-1,new C(1,0),0,1);tiny.add(2,-1,new C(1,0),0,1);
    tiny.dr[3]+=.02;tiny.dr[4]+=.02;double[] solved=tiny.solve(0);
    C actual=new C(.5,0).sub(tiny.val(solved,3)).scale(.02),exact=new C(.5,0).div(z1.add(z2).add(new C(50,0)));
    require(actual.sub(exact).abs()/exact.abs()<2e-7,"Analytic two-material/source series circuit");
    ByteArrayOutputStream bytes=new ByteArrayOutputStream();
    try(DataOutputStream zipped=new DataOutputStream(new GZIPOutputStream(bytes))){put(zipped,-0.0);put(zipped,Math.PI);put(zipped,-1e-237);}
    byte[] raw=new java.util.zip.GZIPInputStream(new ByteArrayInputStream(bytes.toByteArray())).readAllBytes();
    java.nio.ByteBuffer buffer=java.nio.ByteBuffer.wrap(raw).order(java.nio.ByteOrder.LITTLE_ENDIAN);
    require(Double.doubleToRawLongBits(buffer.getDouble())==Double.doubleToRawLongBits(-0.0)&&buffer.getDouble()==Math.PI&&buffer.getDouble()==-1e-237,"Lossless gzip LE Float64");
    System.out.println("SELECTIVITY_SELFTEST partial-face E/J, original baseline operator/E, analytic layered circuit and lossless gzip LE Float64 passed; phantom PDE0");
  }
  public static void main(String[] args)throws Exception{
    Locale.setDefault(Locale.US);
    if(args.length==1&&args[0].equals("--selftest")){selftestSelectivity();return;}
    if(args.length!=5||!args[0].equals("--execute-parent"))throw new IllegalArgumentException("Only exact registered parent execution or --selftest");
    byte[] configBytes=registeredConfig(args[3]);executeParentGuard(args,configBytes);
    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}
    require(p.getProperty("frequencies").equals("3000,3030,9000,9090"),"Fixed carrier/harmonic set");
    int channels=Integer.parseInt(p.getProperty("channels")),sc=Integer.parseInt(p.getProperty("validation.sc_cells"));
    String[] bc=p.getProperty("bulk.counts").split(",");int[] bulk=new int[3];for(int k=0;k<3;k++)bulk[k]=Integer.parseInt(bc[k]);
    String[] layers={"sc","dermis","fat","muscle"};for(int l=0;l<4;l++){SIG[l]=number(p,layers[l]+".sigma");ER[l]=number(p,layers[l]+".epsilon_r");}
    List<double[]> patches=mask(p);ValidationMesh m=new ValidationMesh(number(p,"h_mm"),sc,bulk);
    File dir=new File(args[4]);if(!dir.mkdirs())throw new IOException("Output must be new");
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
